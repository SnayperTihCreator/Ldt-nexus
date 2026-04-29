use std::fs::{read_to_string, write};

use pyo3::{prelude::*, types::PyString};
use pythonize::{depythonize, pythonize};
use serde_json::{json, Value};
use pyo3::types::{PyStringMethods};

pub enum Drivers {
    Json,
    Json5,
    Toml,
    Yaml,
    Memory,
    Custom(Py<PyAny>),
}

impl Drivers {

    pub fn load(&self, py: Python<'_>, path: &str) -> Value{
        match self {
            Drivers::Memory => json!({}),
            Drivers::Json | Drivers::Json5 | Drivers::Toml | Drivers::Yaml => {
                let content = read_to_string(path).unwrap_or_else(|_| "{}".to_string());
                match self {
                    Drivers::Json => serde_json::from_str(&content).unwrap_or(json!({})),
                    Drivers::Json5 => json5::from_str(&content).unwrap_or(json!({})),
                    Drivers::Toml => toml::from_str(&content).unwrap_or(json!({})),
                    Drivers::Yaml => serde_yaml::from_str(&content).unwrap_or(json!({})),
                    _ => unreachable!()
                }
            }            
            Drivers::Custom(obj) => {
                let bound = obj.bind(py);
                let res = bound.call_method1("read", (path,))
                .expect("Ldt-nexus: Custom driver 'read' method failed");
                depythonize(&res).unwrap_or(json!({}))
            }
        }
    }

    pub fn save(&self, py: Python<'_>, path: &str, data: &Value) {
        match self {
            Drivers::Memory => {},
            Drivers::Json | Drivers::Json5 | Drivers::Toml | Drivers::Yaml => {
                let content = match self {
                    Self::Json5 => json5::to_string(&data).unwrap_or_default(),
                    Self::Json => serde_json::to_string_pretty(&data).unwrap_or_default(),
                    Self::Toml => toml::to_string_pretty(&data).unwrap_or_default(),
                    Self::Yaml => serde_yaml::to_string(&data).unwrap_or_default(),
                    _ => unreachable!()
                };

                if let Err(e) = write(path, content){
                    eprintln!("Ldt-nexus Error: Failed to write file {}: {}", path, e);
                }
            },
            Drivers::Custom(obj) => {
                let bound = obj.bind(py);
                let pydata = pythonize(py, &data)
                .expect("Ldt-nexus: Failed to pythonize data for custom driver");
                
                if let Err(e) = bound.call_method1("write", (path, pydata)) {
                    e.print(py);
                }

            }
        }
    }

    pub fn from_args(obj: Bound<'_, PyAny>) -> Self {
        if let Ok(data) = obj.cast::<PyString>() {
            let name  = data.to_str().unwrap_or("json");
            match name {
                "yaml" => Drivers::Yaml,
                "toml" => Drivers::Toml,
                "json5" => Drivers::Json5,
                "memory" => Drivers::Memory,
                _ => Drivers::Json,
            }
        } else {
            Drivers::Custom(obj.unbind())
        }
    }
    
}