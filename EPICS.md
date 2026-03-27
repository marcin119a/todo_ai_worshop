# Epiki — nowe funkcjonalności

## Epic 1: Uwierzytelnianie i multi-tenancy

**Cel:** Każdy użytkownik zarządza własnymi zadaniami — izolacja danych między kontami.

**User Stories:**
- `US-1.1` Jako użytkownik chcę się zarejestrować i zalogować (JWT tokens)
- `US-1.2` Jako użytkownik chcę, żeby moje zadania były widoczne tylko dla mnie
- `US-1.3` Jako admin chcę mieć dostęp do wszystkich zadań i statystyk

**Techniczne:** `app/db/models.py` + nowy `User` model, middleware JWT, scope na repository queries

---

## Epic 2: Kategorie i tagi zadań

**Cel:** Organizacja zadań przez kategorie (projekty) i swobodne tagi.

**User Stories:**
- `US-2.1` Jako użytkownik chcę tworzyć kategorie i przypisywać do nich zadania
- `US-2.2` Jako użytkownik chcę tagować zadania dowolnymi etykietami
- `US-2.3` Jako użytkownik chcę filtrować listę zadań po kategorii/tagu
- `US-2.4` Jako AI chcę uwzględniać kategorię przy sugestii priorytetu

**Techniczne:** nowe modele `Category`, `Tag`, relacje many-to-many, rozszerzenie `GET /tasks/` o filtry

---

## Epic 3: Terminy i zarządzanie deadline'ami

**Cel:** Zadania mają daty wykonania, system ostrzega o przeterminowanych.

**User Stories:**
- `US-3.1` Jako użytkownik chcę ustawić `due_date` przy tworzeniu/edycji zadania
- `US-3.2` Jako użytkownik chcę filtrować zadania przeterminowane (`GET /tasks/?overdue=true`)
- `US-3.3` Jako AI chcę dostawać `due_date` jako kontekst i podnosić priorytet bliskich terminów
- `US-3.4` Jako użytkownik chcę endpoint `GET /tasks/upcoming?days=7` dla zadań na najbliższy tydzień

**Techniczne:** nowe pole `due_date` w modelu, logika w `TaskService`, rozszerzenie `AIPriorityService.suggest_priority()` o parametr `due_date`

---

## Epic 4: Historia zmian i komentarze

**Cel:** Pełna audytowalność — śledzenie kto i kiedy zmienił zadanie oraz możliwość dyskusji.

**User Stories:**
- `US-4.1` Jako użytkownik chcę zobaczyć historię zmian zadania (`GET /tasks/{id}/history`)
- `US-4.2` Jako system chcę automatycznie logować każdą zmianę pola (old value → new value)
- `US-4.3` Jako użytkownik chcę dodawać komentarze do zadań (`POST /tasks/{id}/comments`)
- `US-4.4` Jako użytkownik chcę listować komentarze (`GET /tasks/{id}/comments`)

**Techniczne:** nowe modele `TaskHistory` (event sourcing light), `Comment`, hook w `TaskRepository.update()` do zapisu diff
