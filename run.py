"""
run.py - Main entry point for the Lansia Clustering Web Application.
Runs the Flask development server.
"""

import sys
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5000
    
    print("\n" + "=" * 60)
    print("      SISTEM CLUSTERING RISIKO KESEHATAN LANSIA")
    print("           PUSKESMAS TEMPEH, LUMAJANG")
    print("=" * 60)
    print(f" Server berjalan di: http://{host}:{port}/")
    print(" Silakan buka link tersebut di browser Anda.")
    print(" Tekan Ctrl+C untuk menghentikan server.")
    print("=" * 60 + "\n")
    
    try:
        app.run(host=host, port=port, debug=True)
    except KeyboardInterrupt:
        print("\nServer dihentikan oleh pengguna. Sampai jumpa!")
        sys.exit(0)
