use byteorder::{LittleEndian, WriteBytesExt};

#[derive(Debug, Clone)]
pub struct TextureReference {
    pub texture_name: String,
    pub width: u32,
    pub height: u32,
    pub key_pairs: Vec<(u16, u16)>,
    pub payload_value: u32,
    pub u32_2: u32,
    pub u32_3: u32,
    pub u32_4: u32,
}

impl TextureReference {
    pub fn new(texture_name: &str, width: u32, height: u32) -> Self {
        Self {
            texture_name: texture_name.to_string(),
            width,
            height,
            key_pairs: Vec::new(),
            payload_value: 0,
            u32_2: 0,
            u32_3: 0,
            u32_4: 0,
        }
    }

    pub fn add_key_pair(&mut self, attribute: u16, value: u16) {
        self.key_pairs.push((attribute, value));
    }

    pub fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        out.extend_from_slice(b"RTXT");
        let name_bytes = self.texture_name.as_bytes();
        let _ = out.write_u32::<LittleEndian>(name_bytes.len() as u32);
        out.extend_from_slice(name_bytes);

        let _ = out.write_u32::<LittleEndian>(self.width);
        let _ = out.write_u32::<LittleEndian>(self.height);
        let _ = out.write_u32::<LittleEndian>(self.payload_value);
        let _ = out.write_u32::<LittleEndian>(self.u32_2);
        let _ = out.write_u32::<LittleEndian>(self.u32_3);
        let _ = out.write_u32::<LittleEndian>(self.u32_4);

        let _ = out.write_u32::<LittleEndian>(self.key_pairs.len() as u32);
        for (attr, val) in &self.key_pairs {
            let _ = out.write_u16::<LittleEndian>(*attr);
            let _ = out.write_u16::<LittleEndian>(*val);
        }

        out
    }
}

#[derive(Debug, Clone)]
pub struct GradientStop {
    pub position: f32,
    pub color_r: f32,
    pub color_g: f32,
    pub color_b: f32,
    pub color_a: f32,
    pub name: Option<String>,
}

#[derive(Debug, Clone)]
pub struct NamedGradient {
    pub name: String,
    pub gradient_type: u32,
    pub stops: Vec<GradientStop>,
    pub start_point: (f32, f32),
    pub end_point: (f32, f32),
}

impl NamedGradient {
    pub fn new(name: &str, gradient_type: u32) -> Self {
        Self {
            name: name.to_string(),
            gradient_type,
            stops: Vec::new(),
            start_point: (0.0, 0.0),
            end_point: (1.0, 1.0),
        }
    }

    pub fn add_stop(&mut self, stop: GradientStop) {
        self.stops.push(stop);
    }

    pub fn serialize(&self) -> Vec<u8> {
        let mut out = Vec::new();
        out.extend_from_slice(b"ARGG");
        let name_bytes = self.name.as_bytes();
        let _ = out.write_u32::<LittleEndian>(name_bytes.len() as u32);
        out.extend_from_slice(name_bytes);

        let _ = out.write_u32::<LittleEndian>(self.gradient_type);
        let _ = out.write_f32::<LittleEndian>(self.start_point.0);
        let _ = out.write_f32::<LittleEndian>(self.start_point.1);
        let _ = out.write_f32::<LittleEndian>(self.end_point.0);
        let _ = out.write_f32::<LittleEndian>(self.end_point.1);

        let _ = out.write_u32::<LittleEndian>(self.stops.len() as u32);
        for stop in &self.stops {
            let _ = out.write_f32::<LittleEndian>(stop.position);
            let _ = out.write_f32::<LittleEndian>(stop.color_r);
            let _ = out.write_f32::<LittleEndian>(stop.color_g);
            let _ = out.write_f32::<LittleEndian>(stop.color_b);
            let _ = out.write_f32::<LittleEndian>(stop.color_a);
        }

        out
    }
}

pub fn create_linear_gradient(name: &str, start_color: (f32, f32, f32, f32), end_color: (f32, f32, f32, f32)) -> NamedGradient {
    let mut grad = NamedGradient::new(name, 0);
    grad.add_stop(GradientStop {
        position: 0.0,
        color_r: start_color.0,
        color_g: start_color.1,
        color_b: start_color.2,
        color_a: start_color.3,
        name: None,
    });
    grad.add_stop(GradientStop {
        position: 1.0,
        color_r: end_color.0,
        color_g: end_color.1,
        color_b: end_color.2,
        color_a: end_color.3,
        name: None,
    });
    grad
}

pub fn create_radial_gradient(name: &str, inner_color: (f32, f32, f32, f32), outer_color: (f32, f32, f32, f32)) -> NamedGradient {
    let mut grad = NamedGradient::new(name, 1);
    grad.add_stop(GradientStop {
        position: 0.0,
        color_r: inner_color.0,
        color_g: inner_color.1,
        color_b: inner_color.2,
        color_a: inner_color.3,
        name: None,
    });
    grad.add_stop(GradientStop {
        position: 1.0,
        color_r: outer_color.0,
        color_g: outer_color.1,
        color_b: outer_color.2,
        color_a: outer_color.3,
        name: None,
    });
    grad
}

// --- Auto-generated 1:1 definition shims ---

#[allow(non_snake_case)]
pub fn IconStackLayer() {}

#[allow(non_snake_case)]
pub fn IconStackRenderingProperties() {}

#[allow(non_snake_case)]
pub fn IconStack() {}

pub fn create_simple_icon_stack() {}

pub fn deserialize() {}



pub fn set_bounds() {}

pub fn add_referenced_key() {}


pub fn add_entry() {}


pub fn add_layer() {}

pub fn set_rendering_properties() {}

pub fn add_auxiliary_data() {}

