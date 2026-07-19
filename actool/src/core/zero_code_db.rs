use byteorder::{LittleEndian, WriteBytesExt};
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct ZeroCodeLayer {
    pub name: String,
    pub opacity: f32,
    pub properties: HashMap<String, String>,
}

impl ZeroCodeLayer {
    pub fn new(name: &str, opacity: f32) -> Self {
        Self {
            name: name.to_string(),
            opacity,
            properties: HashMap::new(),
        }
    }

    pub fn set_property(&mut self, key: &str, value: &str) {
        self.properties.insert(key.to_string(), value.to_string());
    }

    pub fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let name_bytes = self.name.as_bytes();
        let _ = out.write_u32::<LittleEndian>(name_bytes.len() as u32);
        out.extend_from_slice(name_bytes);
        let _ = out.write_f32::<LittleEndian>(self.opacity);
        out
    }

    pub fn deserialize(data: &[u8], mut offset: usize) -> Result<(Self, usize), &'static str> {
        if offset + 4 > data.len() { return Err("Truncated layer name len"); }
        let nlen = u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
        offset += 4;

        if offset + nlen > data.len() { return Err("Truncated layer name"); }
        let name = String::from_utf8_lossy(&data[offset..offset + nlen]).to_string();
        offset += nlen;

        if offset + 4 > data.len() { return Err("Truncated layer opacity"); }
        let opacity = f32::from_le_bytes(data[offset..offset + 4].try_into().unwrap());
        offset += 4;

        Ok((Self::new(&name, opacity), offset))
    }
}

#[derive(Debug, Clone)]
pub struct ZeroCodeEffect {
    pub effect_type: u32,
    pub radius: f32,
    pub parameters: HashMap<String, f32>,
}

impl ZeroCodeEffect {
    pub fn new(effect_type: u32, radius: f32) -> Self {
        Self {
            effect_type,
            radius,
            parameters: HashMap::new(),
        }
    }

    pub fn set_parameter(&mut self, key: &str, value: f32) {
        self.parameters.insert(key.to_string(), value);
    }

    pub fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let _ = out.write_u32::<LittleEndian>(self.effect_type);
        let _ = out.write_f32::<LittleEndian>(self.radius);
        out
    }

    pub fn deserialize(data: &[u8], mut offset: usize) -> Result<(Self, usize), &'static str> {
        if offset + 8 > data.len() { return Err("Truncated effect data"); }
        let etype = u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap());
        let radius = f32::from_le_bytes(data[offset + 4..offset + 8].try_into().unwrap());
        offset += 8;

        Ok((Self::new(etype, radius), offset))
    }
}

#[derive(Debug, Clone)]
pub struct ZeroCodePath {
    pub points: Vec<(f32, f32)>,
    pub is_closed: bool,
}

impl ZeroCodePath {
    pub fn new(points: Vec<(f32, f32)>, is_closed: bool) -> Self {
        Self { points, is_closed }
    }

    pub fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let _ = out.write_u32::<LittleEndian>(self.points.len() as u32);
        out.push(if self.is_closed { 1 } else { 0 });
        for &(x, y) in &self.points {
            let _ = out.write_f32::<LittleEndian>(x);
            let _ = out.write_f32::<LittleEndian>(y);
        }
        out
    }
}

#[derive(Debug, Clone)]
pub struct ZeroCodeBezel {
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub layers: Vec<ZeroCodeLayer>,
    pub effects: Vec<ZeroCodeEffect>,
}

impl ZeroCodeBezel {
    pub fn new(name: &str, width: u32, height: u32) -> Self {
        Self {
            name: name.to_string(),
            width,
            height,
            layers: Vec::new(),
            effects: Vec::new(),
        }
    }

    pub fn add_layer(&mut self, layer: ZeroCodeLayer) {
        self.layers.push(layer);
    }

    pub fn add_effect(&mut self, effect: ZeroCodeEffect) {
        self.effects.push(effect);
    }

    pub fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let name_bytes = self.name.as_bytes();

        let _ = out.write_u32::<LittleEndian>(name_bytes.len() as u32);
        out.extend_from_slice(name_bytes);
        let _ = out.write_u32::<LittleEndian>(self.width);
        let _ = out.write_u32::<LittleEndian>(self.height);

        let _ = out.write_u32::<LittleEndian>(self.layers.len() as u32);
        for l in &self.layers {
            out.extend_from_slice(&l.serialize());
        }

        let _ = out.write_u32::<LittleEndian>(self.effects.len() as u32);
        for e in &self.effects {
            out.extend_from_slice(&e.serialize());
        }

        out
    }

    pub fn deserialize(data: &[u8]) -> Result<Self, &'static str> {
        if data.len() < 16 { return Err("Truncated bezel data"); }
        let nlen = u32::from_le_bytes(data[0..4].try_into().unwrap()) as usize;
        let mut offset = 4;

        if offset + nlen > data.len() { return Err("Truncated bezel name"); }
        let name = String::from_utf8_lossy(&data[offset..offset + nlen]).to_string();
        offset += nlen;

        if offset + 8 > data.len() { return Err("Truncated bezel size"); }
        let width = u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap());
        let height = u32::from_le_bytes(data[offset + 4..offset + 8].try_into().unwrap());
        offset += 8;

        let mut bezel = Self::new(&name, width, height);

        if offset + 4 <= data.len() {
            let layer_count = u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
            offset += 4;
            for _ in 0..layer_count {
                let (layer, new_off) = ZeroCodeLayer::deserialize(data, offset)?;
                bezel.add_layer(layer);
                offset = new_off;
            }
        }

        if offset + 4 <= data.len() {
            let effect_count = u32::from_le_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
            offset += 4;
            for _ in 0..effect_count {
                let (effect, new_off) = ZeroCodeEffect::deserialize(data, offset)?;
                bezel.add_effect(effect);
                offset = new_off;
            }
        }

        Ok(bezel)
    }
}

#[derive(Debug, Clone)]
pub struct ZeroCodeGlyph {
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub paths: Vec<ZeroCodePath>,
}

impl ZeroCodeGlyph {
    pub fn new(name: &str, width: u32, height: u32) -> Self {
        Self {
            name: name.to_string(),
            width,
            height,
            paths: Vec::new(),
        }
    }

    pub fn add_path(&mut self, path: ZeroCodePath) {
        self.paths.push(path);
    }

    pub fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let name_bytes = self.name.as_bytes();
        let _ = out.write_u32::<LittleEndian>(name_bytes.len() as u32);
        out.extend_from_slice(name_bytes);
        let _ = out.write_u32::<LittleEndian>(self.width);
        let _ = out.write_u32::<LittleEndian>(self.height);

        let _ = out.write_u32::<LittleEndian>(self.paths.len() as u32);
        for p in &self.paths {
            out.extend_from_slice(&p.serialize());
        }

        out
    }
}

pub struct ZeroCodeDatabase {
    pub name: String,
    pub bezels: HashMap<String, ZeroCodeBezel>,
    pub glyphs: HashMap<String, ZeroCodeGlyph>,
}

impl ZeroCodeDatabase {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            bezels: HashMap::new(),
            glyphs: HashMap::new(),
        }
    }

    pub fn add_bezel(&mut self, bezel: ZeroCodeBezel) {
        self.bezels.insert(bezel.name.clone(), bezel);
    }

    pub fn add_glyph(&mut self, glyph: ZeroCodeGlyph) {
        self.glyphs.insert(glyph.name.clone(), glyph);
    }

    pub fn get_bezel(&self, name: &str) -> Option<&ZeroCodeBezel> {
        self.bezels.get(name)
    }

    pub fn get_glyph(&self, name: &str) -> Option<&ZeroCodeGlyph> {
        self.glyphs.get(name)
    }

    pub fn serialize_bezels(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let _ = out.write_u32::<LittleEndian>(self.bezels.len() as u32);
        for bezel in self.bezels.values() {
            out.extend_from_slice(&bezel.serialize());
        }
        out
    }

    pub fn serialize_glyphs(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let _ = out.write_u32::<LittleEndian>(self.glyphs.len() as u32);
        for glyph in self.glyphs.values() {
            out.extend_from_slice(&glyph.serialize());
        }
        out
    }
}
