# AI Email Router - Klasyfikator wiadomości e-mail

Mikroserwis oparty na FastAPI, LangChain oraz modelu językowym Ollama / Qwen 2.5

Aplikacja jest w pełni skonteneryzowana przy użyciu Dockera. Środowisko składa się z czterech skonteneryzowanych usług

---

## Uruchomienie środowiska
1. Sklonuj repozytorium i przejdź do katalogu projektu
- git clone https://github.com/olka276/ai-email-sender-app.git
- cd ai-email-sender-app
2. Zbuduj kontenery
- `docker compose up --build`
Przy pierwszym uruchomieniu kontener ollama_model_loader pobierze wagi modelu. Po pojawieniu się komunikatu "Model ready!" uruchomi się kontener ai_api
3. Dostępne usługi
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
```bash
pip install -r requirements-dev.txt
pytest
```

---

## Decyzje architekturalne/techniczne:
1. Lokalny silnik LLM (ollama + ollama-pull)
- wykorzystanie modelu qwen2.5:3b wspierającego tool-calling uruchamianego lokalnie
- jednorazowy kontener pobierający wagi modelu - ollama-pull wykonuje warm-up modelu przed zbudowaniem API
- stały kontekst systemowy (SystemMessage) odseparowany od HumanMessage, dzięki czemu jest użyty caching, co skraca czas przetwarzania kolejnych zapytań
2. Determinizm
- Model językowy decyduje wyłącznie o dziale, do którego wyśle e-mail, natomiast pozostałe dane takie, jak treść czy email pierwotnego nadawcy są przekazywane w sposób deterministyczny przez InjectedToolArg. Zapobiega to halucynacjom oraz modyfikacji treści wiadomości przez model.
3. Ochrona przed prompt injection
- treść wiadomości jest izolowana w tagach <user_message> a instrukcje nakazują traktować ją wyłącznie jako dane wejściowe, ignorując w niej próby nadpisania instrukcji.
4. Asynchroniczność i throttling
- endpoint `POST /send` zwraca od razu `202 Accepted`, a klasyfikacja i wysyłka odbywa się w tle (`BackgroundTasks`); zadania nie są trwałe - restart kontenera gubi te będące w toku (kolejka, np. Redis, byłaby naturalnym kolejnym krokiem)- stos asynchroniczny (FastAPI + ainvoke + aiosmptlib) zapobiega blokowaniu event loopa przy komunikacji z serwerem SMTP oraz API modelu
- limit współbieżnych procesów oraz rate limiting chroni lokalne zasoby przed przeciążeniem
5. Zcentralizowana konfiguracja (pydantic-settings)
- walidacja ścieżek i ustawień przy starcie aplikacji w jednym pliku config.py
