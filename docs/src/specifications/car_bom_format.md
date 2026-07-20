# 01: CoreUI CAR File & BOMStore Binary Architecture

This document provides a field-by-field, byte-by-byte technical specification of Apple `.car` archives and the underlying `BOMStore` container format.

---

## Architecture Diagram

![Apple CoreUI CAR Archive & BOMStore Binary Layout](../images/car_binary_layout.png)

---

## 1. BOMStore Container (32-Byte Header)

All `.car` archives are Big-Endian `BOMStore` containers:

```
+-------------------------------------------------------------------------+
| BOMHeader (32 Bytes)                                                    |
| Magic: b"BOMStore", Version: 1, Block Count, Offsets & Lengths          |
+-------------------------------------------------------------------------+
| Block Payload Area                                                      |
| Block 1 (CARHEADER), Block 2 (KEYFORMAT), Block 3... (CSIs, Trees)      |
+-------------------------------------------------------------------------+
| Block Index Table                                                       |
| Capacity, [Offset (u32), Length (u32)] x Capacity                       |
+-------------------------------------------------------------------------+
| Variables Table                                                         |
| Count, [Block ID (u32), Name Length (u8), Name (UTF-8 Bytes)] x Count    |
+-------------------------------------------------------------------------+
```

### BOMHeader Field Specification

| Offset | Type / Size | Field Name | Description |
| :--- | :--- | :--- | :--- |
| `0..8` | `char[8]` | `magic` | `b"BOMStore"` (ASCII) |
| `8..12` | `uint32_t` | `version` | Version number. Always `1` (0x00000001) |
| `12..16` | `uint32_t` | `block_count` | Number of active blocks (`capacity - 1`) |
| `16..20` | `uint32_t` | `index_offset` | Absolute offset to Block Index Table |
| `20..24` | `uint32_t` | `index_length` | Byte size of Index Table (`4 + capacity * 8`) |
| `24..28` | `uint32_t` | `vars_offset` | Absolute offset to Variables Table |
| `28..32` | `uint32_t` | `vars_length` | Byte size of Variables Table |

---

## 2. CARHeader (436 Bytes)

The block referenced by the `"CARHEADER"` variable contains a 436-byte header:

| Offset | Type / Size | Field Name | Description |
| :--- | :--- | :--- | :--- |
| `0..4` | `char[4]` | `magic` | `b"CTAR"` (Big-Endian) or `b"RATC"` (Little-Endian) |
| `4..8` | `uint32_t` | `core_ui_version` | CoreUI format version (Standard: `975`) |
| `8..12` | `uint32_t` | `storage_version` | Storage version (Standard: `1`) |
| `12..16` | `uint32_t` | `storage_timestamp` | Creation Epoch timestamp |
| `16..20` | `uint32_t` | `rendition_count` | Total renditions in the archive |
| `20..148` | `char[128]` | `main_version` | Tool identifier (e.g. `"actool 0.1.0"`) |
| `148..404` | `char[256]` | `version_string` | Extended version description |
| `404..420` | `uint8_t[16]` | `uuid` | Randomly generated 128-bit UUID (v4) |
| `420..424` | `uint32_t` | `associated_checksum` | Checksum value |
| `424..428` | `uint32_t` | `schema_version` | Schema version (Standard: `1`) |
| `428..432` | `uint32_t` | `color_space_id` | Default color space (sRGB: `1`) |
| `432..436` | `uint32_t` | `key_semantics` | Key semantics flag (Standard: `1`) |

---

## 3. CoreStructuredImage (CSI) Fixed Header (184 Bytes)

CSI blocks store individual asset renditions:

```
+-------------------------------------------------------------------------+
| CSI Fixed Header (184 Bytes)                                            |
| Magic (4B): "ISTC" / "CTSI", Version: 1, Width, Height, Scale           |
| Pixel Format (4B): BGRA / 8AG / COLR / DATA / AS44 / AS88              |
| Layout (4B): 1000 Direct, 1002 Stack, 1003 Link, 1004 Atlas             |
| Asset Name (128B Null-Padded UTF-8)                                     |
| Offset 168..172: TLV Length (u32)                                       |
| Offset 172..176: Flag 1 (u32)                                           |
| Offset 176..180: Zero (u32)                                             |
| Offset 180..184: Payload Length (u32)                                   |
+-------------------------------------------------------------------------+
```

### Key Field Offsets
- **Offset `168..172`**: $L_{TLV}$ (TLV Stream Length in bytes)
- **Offset `172..176`**: `1` (Flag)
- **Offset `176..180`**: `0` (Zero)
- **Offset `180..184`**: $L_{Payload}$ (Compressed Payload Length in bytes)
