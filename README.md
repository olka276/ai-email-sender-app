# AI Email Router - Klasyfikator wiadomości e-mail

Mikroserwis oparty na FastAPI, LangChain oraz modelu językowym Ollama / Qwen 2.5

Aplikacja jest w pełni skonteneryzowana przy użyciu Dockera. Środowisko składa się z trzech usług: `api` (FastAPI), `ollama` (silnik LLM) oraz `mailhog` (przechwytywanie maili)

---

## Uruchomienie środowiska
1. Sklonuj repozytorium i przejdź do katalogu projektu
- git clone https://github.com/olka276/ai-email-sender-app.git
- cd ai-email-sender-app
2. (Opcjonalnie) Dostosuj konfigurację: `cp .env.example .env`. Wszystkie zmienne mają wartości domyślne, więc bez `.env` całość też działa
3. Uruchom środowisko
- `docker compose up -d --build`
Przy pierwszym uruchomieniu kontener `ollama` pobierze wagi modelu (do `./ollama_data`) i go rozgrzeje, co może potrwać kilka minut. Kontener `ollama` jest `healthy` dopiero po komunikacie "Model ready!", dopiero wtedy startuje `api` (`docker compose up --wait` czeka na całość). Postęp: `docker logs -f ollama_engine`
4. Dostępne usługi (porty z `.env`, domyślnie)
- Swagger: http://localhost:8000/api/v1/docs
- Healthcheck: http://localhost:8000/api/v1/health
- Mailhog UI: http://localhost:8025

Przykładowe zapytanie cURL

```bash 
curl -X POST "http://localhost:8000/api/v1/send" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jan.kowalski@firma.pl",
    "message": "Dzień dobry, chciałbym złożyć wniosek o zwolnienie lekarskie (L4) oraz uzyskać zaświadczenie o zarobkach."
  }'
```

oczekiwana odpowiedź (202 Accepted):
```bash
{
   "status": "accepted"
}
```

Zgłoszenie jest przetwarzane w tle (FastAPI `BackgroundTasks`). Po kilku sekundach (zależnie od czasu odpowiedzi modelu) wiadomość pojawi się w skrzynce Mailhoga z ustawionym Reply-To oryginalnego nadawcy. Ewentualne błędy przetwarzania są zapisywane w logach kontenera `ai_api`.

## Testy
Testy (pytest) nie wymagają Ollamy ani Mailhoga - LLM i SMTP są mockowane.
Zależności są zarządzane przez [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`).

Lokalnie:
```bash
uv sync
uv run pytest
```

Albo w Dockerze (bez instalowania czegokolwiek na hoście):
```bash
docker run --rm -v "$PWD":/src:ro -e PYTHONDONTWRITEBYTECODE=1 -e UV_LINK_MODE=copy \
  ghcr.io/astral-sh/uv:python3.12-bookworm-slim sh -c \
  'cp -r /src /work && cd /work && uv sync --frozen -q && uv run pytest -q -p no:cacheprovider'
```

---

## Decyzje architekturalne/techniczne:
1. Lokalny silnik LLM (ollama)
- wykorzystanie modelu qwen2.5:3b wspierającego tool-calling uruchamianego lokalnie
- pobranie wag i warm-up modelu odbywają się w `entrypoint` kontenera `ollama` (bez dodatkowego kontenera); healthcheck jest zielony dopiero, gdy model jest gotowy, a `api` czeka na `service_healthy`
- wagi są mapowane do katalogu `./ollama_data` na hoście, co ułatwia ich przenoszenie i redystrybucję (katalog jest w `.gitignore`; pliki należą do roota, bo Ollama działa w kontenerze jako root)
- stały kontekst systemowy (SystemMessage) odseparowany od HumanMessage, dzięki czemu jest użyty caching, co skraca czas przetwarzania kolejnych zapytań
2. Determinizm
- Model językowy decyduje wyłącznie o dziale, do którego wyśle e-mail, natomiast pozostałe dane takie, jak treść czy email pierwotnego nadawcy są przekazywane w sposób deterministyczny przez InjectedToolArg. Zapobiega to halucynacjom oraz modyfikacji treści wiadomości przez model.
3. Ochrona przed prompt injection
- treść wiadomości jest izolowana w tagach <user_message> a instrukcje nakazują traktować ją wyłącznie jako dane wejściowe, ignorując w niej próby nadpisania instrukcji.
4. Asynchroniczność i throttling
- endpoint `POST /send` zwraca od razu `202 Accepted`, a klasyfikacja i wysyłka odbywa się w tle (`BackgroundTasks`); zadania nie są trwałe - restart kontenera gubi te będące w toku (kolejka, np. Redis, byłaby naturalnym kolejnym krokiem)
- stos asynchroniczny (FastAPI + ainvoke + aiosmptlib) zapobiega blokowaniu event loopa przy komunikacji z serwerem SMTP oraz API modelu
- limit współbieżnych procesów oraz rate limiting chroni lokalne zasoby przed przeciążeniem
5. Zcentralizowana konfiguracja (pydantic-settings)
- walidacja ścieżek i ustawień przy starcie aplikacji w jednym pliku config.py
- porty i parametry modelu są sterowane zmiennymi środowiskowymi z `.env` (wzorzec: `.env.example`), a compose ma wartości domyślne, więc `docker compose up -d` działa po samym sklonowaniu
- ustawienia aplikacji (nadawca SMTP, limity współbieżności, kontekst modelu, poziom logów itd.) trafiają do kontenera `api` przez `env_file: .env`, a ich domyślne wartości są zdefiniowane w jednym miejscu - `app/config.py`. Wszystkie pola `Settings` można nadpisać zmienną o tej samej nazwie wielkimi literami; lista w `.env.example`
- `ollama_temperature=0` jest celowo poza konfiguracją środowiskową - to decyzja projektowa (determinizm klasyfikacji)
- Ollama nie jest wystawiona na host - jest dostępna tylko w sieci compose
6. Logowanie i obsługa błędów
- błędy domenowe (`LLMUnavailableError`, `EmailDeliveryError`) dziedziczą po `EmailProcessingError` i są rozróżniane w logach; nieoczekiwane wyjątki są logowane ze stack trace
- logger jest wstrzykiwany przez `Depends` (`dependencies.get_logger`), poziom ustawia zmienna `LOG_LEVEL` (domyślnie `INFO`)
- klient nigdy nie dostaje szczegółów błędu wewnętrznego
7. Zarządzanie zależnościami i obraz
- `uv` z lockfile'em (`uv.lock`) zapewnia odtwarzalny build; obraz instaluje zależności w osobnej warstwie (cache) komendą `uv sync --frozen --no-dev`
- `.dockerignore` wyklucza m.in. `ollama_data` (wagi modelu) z kontekstu builda
