import qrcode
import os
import json

def generate_qr(reg_number, full_name="", course="", save_folder="static/qrcodes"):
    """
    Create a QR code image encoding student details as JSON.
    """
    os.makedirs(save_folder, exist_ok=True)
    
    # Encode student details as JSON in the QR code
    qr_data = json.dumps({
        "reg_number": reg_number,
        "full_name": full_name,
        "course": course
    })
    
    qr = qrcode.make(qr_data)
    path = os.path.join(save_folder, f"{reg_number}.png")
    qr.save(path)
    return path