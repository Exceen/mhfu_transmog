# In-Game Transmog Picker (v3.0)

One cheat code, installed once; looks are then picked in the game. For MHFU (ULJM05500) with
FUComplete v1.4.0. Get the code from the website's *In-Game Picker* tab or from
[`transmog_codes.txt`](transmog_codes.txt) (PPSSPP: one cheat, real PSP: 14 parts, enable all of them).

## Use

Item box → Arrange Items → Equipment:

1. Pick up the piece whose look you want (**Circle**).
2. Move to the piece that should get that look and press **Square** instead of Circle
   ("confirm" sound). If that piece is equipped, your hunter changes at once.
3. To undo: pick up the piece and press **Square** on it ("cancel" sound).

Both pieces must be the same slot, weapons the same weapon class; otherwise you hear the error
sound and keep the piece picked up. Without a picked-up piece, Square shows the Info window as usual.
You can only use looks of pieces that are in your box.

## Good to know

- A look belongs to the kind of piece, not to the single item: all your "Mafumofu Jackets" change.
- The looks are saved in `ms0:/PSP/SAVEDATA/MHFU_TRANSMOG.BIN`, not in your save data, and are
  shared by all characters. Delete the file to reset everything. At most 127 kinds of pieces can
  have a look; a 128th gives the error sound and changes nothing.
- It patches the same tables as the website's codes. Don't use a website code and an in-game look
  for the same piece. The Multiplayer codes work with it as before.
- Other players who wear a piece you gave a look are shown with that look on your screen, unless
  they send their own look with the Multiplayer codes (same as with the website's codes).

## Build

`python3 ingame/build.py` (needs [armips](https://github.com/Kingcom/armips)) writes
`../ingame_codes.json` (website) and `transmog_codes.txt`. Technical notes:
[FINDINGS.md, section 14](../FINDINGS.md).
