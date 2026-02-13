"""
Test capture frame Twitch - Béthune
"""

import subprocess
import os
from datetime import datetime


def capture_twitch_frame(channel, output_path):
    """
    Capture une frame depuis un stream Twitch
    """
    twitch_url = f"https://www.twitch.tv/{channel}"

    cmd = (
        f"streamlink {twitch_url} best --stdout | "
        f"ffmpeg -i pipe:0 -vframes 1 -q:v 2 {output_path} -y"
    )

    print(f"  🎬 Connexion au stream Twitch : {twitch_url}")
    print(f"  ⏳ Capture en cours (peut prendre 10-20 sec)...")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            timeout=30,
            capture_output=True,
            text=True
        )

        # Vérifier si l'image a été créée
        if os.path.exists(output_path):
            size = os.path.getsize(output_path) / 1024
            print(f"  ✓ Frame capturée : {output_path} ({size:.1f} KB)")
            return True
        else:
            print(f"  ✗ Fichier non créé")
            print(f"  stderr : {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        print("  ✗ Timeout (30s dépassé)")
        return False
    except Exception as e:
        print(f"  ✗ Erreur : {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST CAPTURE - Grand'Place Béthune (Twitch)")
    print("=" * 60 + "\n")

    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    output = f"bethune_{now}.jpg"

    success = capture_twitch_frame("villebethunegplace", output)

    if success:
        print(f"\n✅ SUCCÈS ! Image : {output}")
        print("💡 Vous pouvez maintenant tester YOLO dessus")
    else:
        print(f"\n❌ ÉCHEC")