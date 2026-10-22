# CleanStay VIT project review

## Corrections applied

1. Fixed the custom authentication backend path in `accounts/views.py`.
   - Old: `accounts.backends.EmailOrPhoneBackend`
   - Correct: `accounts.backend.EmailOrPhoneBackend`

2. Registered the custom email-or-phone backend in `config/settings.py`.

3. Changed cleaner redirects to the real cleaner dashboard (`cleaner_home`) instead of the placeholder dashboard.

4. Reworked `cleaners/views.py`:
   - Removed duplicate imports.
   - Enforced cleaner-only access.
   - Enforced POST for status updates.
   - Saved only the required status fields.
   - Passed the cleaner profile into the request-detail template.

5. Changed the default login redirect to `/dashboard/` so role-based routing decides the correct portal.

6. Removed the exposed Google OAuth client secret from Django's `SECRET_KEY` setting.
   - Use the `DJANGO_SECRET_KEY` environment variable before production.

7. Confirmed all Python files compile successfully with `compileall`.

## Local verification commands

Activate your Windows virtual environment, then run:

```powershell
python manage.py check
python manage.py runserver
```

Test these routes:

- `/warden/`
- `/warden/requests/1/` (replace 1 with an existing MH A request ID)
- `/cleaner/`
- `/dashboard/`

## Important security note

The Google OAuth client secret was previously used as Django's `SECRET_KEY` and was visible in project code/screenshots. Rotate that Google OAuth client secret in Google Cloud Console before deployment.
