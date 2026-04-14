import qrcode
import os
from django.conf import settings

def generate_qr(data, filename):
    folder = os.path.join(settings.MEDIA_ROOT, "qr_codes")
    os.makedirs(folder, exist_ok=True)

    file_path = os.path.join(folder, filename)

    img = qrcode.make(data)
    img.save(file_path)

    return f"qr_codes/{filename}"