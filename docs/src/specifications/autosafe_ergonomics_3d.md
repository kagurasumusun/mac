# 03: Perceptual Ergonomics, Auto-Safe Guards & 3D Assets

This document details the ISO/CIE 11664-6 CIEDE2000 JND color difference formulas, 80dB SNR HAS psychoacoustics, AutoSafe 4-gate barriers, **Dirty Alpha Protection**, and PBR 3D ORM map consolidation.

---

## 4-Gate Safety Diagram

![4-Gate Auto-Safe Quality Barriers & Perceptual Protection](../images/autosafe_4gate_protection.png)

---

## 1. ISO/CIE 11664-6 CIEDE2000 ($\Delta E_{00} \le 1.0$) Formula

CIEDE2000 models human visual perception (HVS) with extreme accuracy:

$$\Delta E_{00} = \sqrt{\left(\frac{\Delta L'}{S_L}\right)^2 + \left(\frac{\Delta C'}{S_C}\right)^2 + \left(\frac{\Delta H'}{S_H}\right)^2 + R_T \left(\frac{\Delta C'}{S_C}\right)\left(\frac{\Delta H'}{S_H}\right)}$$

- **JND Limit ($\Delta E_{00} \le 1.0$)**: Below 1.0, 100% of human observers cannot distinguish any color difference.

---

## 2. Auto-Domain Safety & Dirty Alpha Auto-Protection

When `A = 0`, non-zero RGB values can contain vital data for Metal custom shaders, 3D heightmaps, or bilinear filtering bleed padding.

- **`AlphaCharacteristic::DirtyAlpha` Detection**: Automatically flags images with $A=0$ and non-zero RGB channels.
- **Dirty Alpha Protection**: When `asset_kind == "texture"`, `domain == ImageDomain::PBRMaterial`, or `SafetyLevel::CustomShaderSafe` / `StrictLossless` is requested, `clean_alpha` zeroing is completely bypassed, preserving exact source bytes and preventing black border halo artifacts around transparent edges.

---

## 3. 3D PBR ORM Map & Tangent Normal Map Packing

- **ORM Packing**: Occlusion (R), Roughness (G), and Metallic (B) are packed into a single BGRA texture, reducing VRAM usage by **66% (1/3)**.
- **Tangent Normal Maps**: Packs $N_x$ in R and $N_y$ in G; $N_z$ is reconstructed on Metal GPU:

$$N_z = \sqrt{1.0 - N_x^2 - N_y^2}$$
