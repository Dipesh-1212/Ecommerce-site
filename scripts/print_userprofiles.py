import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'greatkart.settings')

try:
    import django
    django.setup()
    from accounts.models import UserProfile
    ups = list(UserProfile.objects.all())
    if not ups:
        print('No UserProfile records found')
    for up in ups:
        user = getattr(up.user, 'email', repr(up.user))
        print(f'user={user} | profile_picture={repr(getattr(up.profile_picture, "name", None))}')
except Exception as e:
    import traceback
    traceback.print_exc()
    print('ERROR:', e)
