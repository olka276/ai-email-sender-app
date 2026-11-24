from enum import Enum


class Department(str, Enum):
    HUMAN_RESOURCES = "human_resources"
    KADRY = "kadry"
    HELP_DESK = "help_desk"
    IT = "it"
    OTHER = "other"
