# Firmware Setup (CB3S / BK7231N)

This folder is for OpenBeken flashing tools and device scripts.

## Clone bk7231flasher

```bash
git clone https://github.com/OpenBekenIOT/bk7231flasher.git
cd bk7231flasher
```

## Install Python requirements

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
# Example of a direct dependency often required:
python3 -m pip install pyserial
```

Use the flasher documentation from the repository for your exact adapter and wiring procedure.
