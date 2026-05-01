use std::fs::{File, create_dir_all, read_to_string, write};
use std::io::{BufReader, ErrorKind};
use std::path::Path;

use pyo3::exceptions::*;
use pyo3::prelude::*;
use pythonize::{depythonize, pythonize};
use serde_json::{json, Value};
pub enum Drivers {
    Json,
    Json5,
    Toml,
    Yaml,
    Memory,
    Custom(Py<PyAny>),
}

impl Drivers {

    pub fn load(&self, py: Python<'_>, path: &str) -> PyResult<Value>{
        match self {
            Drivers::Memory => Ok(json!({})),
            Drivers::Custom(obj) => {
                let bound = obj.bind(py);
                let res = bound.call_method1("read", (path,))?;
                depythonize(&res).map_err(|e| PyTypeError::new_err(format!("Failed to depythonize custom driver data: {}", e)))
            },
            _ => {
                let file = match File::open(path) {
                    Ok(f) => f,
                    Err(ref e) if e.kind() == ErrorKind::NotFound => return Ok(json!({})),
                    Err(e) => return Err(PyIOError::new_err(format!("Failed to open config file: {}", e)))
                };
                let reader = BufReader::new(file);
                match self {
                    Drivers::Json => serde_json::from_reader(reader)
                    .map_err(|e| PyTypeError::new_err(format!("JSON parse error: {}", e))),
                    Drivers::Json5 => {
                        let content = read_to_string(path)?;
                        json5::from_str(&content).map_err(|e| PyTypeError::new_err(format!("JSON5 parse error: {}", e)))
                    },
                    Drivers::Toml => {
                        let content = read_to_string(path)?;
                        toml::from_str(&content).map_err(|e| PyTypeError::new_err(format!("TOML parse error: {}", e)))
                    },
                    Drivers::Yaml => serde_yaml::from_reader(reader)
                    .map_err(|e| PyTypeError::new_err(format!("YAML parse error: {}", e))),
                    _ => unreachable!()
                    
                }
            }
        }
    }

    pub fn save(&self, py: Python<'_>, path: &str, data: &Value) -> PyResult<()> {
        match self {
            Drivers::Memory => Ok(()),
            Drivers::Custom(obj) => {
                let bound = obj.bind(py);
                let pydata = pythonize(py, &data)
                .map_err(|e| PyTypeError::new_err(format!("Failed to pythonize data: {}", e)))?;
                bound.call_method1("write", (path, pydata))?;
                Ok(())
            },

            _ => {
                if let Some(parent) = Path::new(path).parent() {
                    create_dir_all(parent)?;
                } 

                let content = match self {
                    Drivers::Json => serde_json::to_string_pretty(data).unwrap(),
                    Drivers::Json5 => json5::to_string(data).unwrap(),
                    Drivers::Toml => toml::to_string_pretty(data).unwrap(),
                    Drivers::Yaml => serde_yaml::to_string(data).unwrap(),
                    _ => unreachable!()
                };

                write(path, content)?;
                Ok(())
            }
        }
    }

    pub fn from_args(obj: Bound<'_, PyAny>) -> PyResult<Self> {
        if let Ok(name) = obj.extract::<String>() {
            match name.to_lowercase().as_str() {
                "json" => Ok(Drivers::Json),
                "json5" => Ok(Drivers::Json5),
                "toml" => Ok(Drivers::Toml),
                "yaml" => Ok(Drivers::Yaml),
                "memory" => Ok(Drivers::Memory),
                _ => Err(pyo3::exceptions::PyValueError::new_err(format!("Unknown driver: {}", name))),
            }
        } else {
            if obj.hasattr("read")? && obj.hasattr("write")? {
                Ok(Drivers::Custom(obj.unbind()))
            } else {
                Err(pyo3::exceptions::PyTypeError::new_err(
                    "Driver must be a string (name) or an object with 'read' and 'write' methods"
                ))
            }
        }
    }

}