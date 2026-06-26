import os
import django

# 1. Yahan humne 'your_project_name' ko badal kar aapke asli project ka naam 'apna_medical_app' ya 'ApnaMedica' jo bhi settings.py ka main folder hai, wo set karna hai.
# Agar aapke main project folder ka naam kuch aur hai, toh 'ApnaMedica' ki jagah wo likhein.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ApnaMedica.settings') 
django.setup()

from customer.models import Medicine 

# Dawaiyo ki list jo database mein jayegi
medicines_list = [
    {"name": "Paracetamol 500mg", "price": 40.0, "category": "Pain Relief"},
    {"name": "Paracetamol 650mg", "price": 60.0, "category": "Pain Relief"},
    {"name": "Pantocid 40mg", "price": 120.0, "category": "OTC Medicines"},
    {"name": "Amoxicillin 500mg", "price": 150.0, "category": "Antibiotics"},
    {"name": "Limcee Vitamin C", "price": 25.0, "category": "Vitamins"},
]

for med in medicines_list:
    obj, created = Medicine.objects.get_or_create(
        name=med["name"],
        defaults={"price": med["price"], "category": med["category"]}
    )
    if created:
        print(f"🎉 Added: {med['name']}")
    else:
        print(f"✔ Already exists: {med['name']}")

print("✅ Saari medicines database mein successfully jor di gayi hain!")