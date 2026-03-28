import os
import django
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "greatkart.settings")
django.setup()

from accounts.models import Account, UserProfile

# Create or get user
user, created = Account.objects.get_or_create(email="testupload@example.com", username="testupload", first_name="Test", last_name="User")
if created:
    user.set_password("password123")
    user.is_active = True
    user.save()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')
client = Client()
client.login(email="testupload@example.com", password="password123")

# Create a dummy image
image_content = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xF9\x04\x01\x0A\x00\x01\x00\x2C\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4C\x01\x00\x3B' # 1x1 GIF
avatar = SimpleUploadedFile("avatar.gif", image_content, content_type="image/gif")

response = client.post('/accounts/edit_profile/', {
    'first_name': 'Test',
    'last_name': 'User',
    'phone_number': '1234567890',
    'email': 'testupload@example.com',
    'address_line_1': 'Addr 1',
    'address_line_2': 'Addr 2',
    'city': 'City',
    'state': 'State',
    'country': 'Country',
    'profile_picture': avatar
})

print("Status Code:", response.status_code)

userprofile = UserProfile.objects.get(user=user)
print("Profile Picture in DB:", userprofile.profile_picture.name)
if userprofile.profile_picture:
    try:
        print("Does file exist?", os.path.exists(userprofile.profile_picture.path))
    except (ValueError, Exception) as e:
        print("Error checking path:", str(e))
else:
    print("No profile picture saved.")
