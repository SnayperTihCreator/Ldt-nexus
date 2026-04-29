use pyo3::prelude::*;
use pyo3_stub_gen::derive::*;
use serde_json::Value;
use pythonize::{depythonize, pythonize};

use crate::drivers::Drivers;


#[gen_stub_pyclass]
#[pyclass]
pub struct LdtSettingEngine {
    #[pyo3(get)]
    pub path: String,

    data: Value,
    driver: Drivers,
    stack: Vec<String>
}

#[gen_stub_pymethods]
#[pymethods]
impl LdtSettingEngine {

    #[new]
    #[pyo3(signature = (path, driver=None))]
    pub fn new(py: Python<'_>,  path: String, driver: Option<Bound<'_, PyAny>>) -> PyResult<Self>{
        let driver_enum = match driver {
            Some(obj) => Drivers::from_args(obj),
            None => Drivers::Json,
        };

        let data = driver_enum.load(py, &path);

        Ok(Self { path, data, driver: driver_enum, stack: Vec::new() })

    }

    // Group

    pub fn begin_group(&mut self, name: String){
        self.stack.push(name);
    }

    pub fn end_group(&mut self){
        self.stack.pop();
    }
    
    pub fn group(&self) -> String {
        self.stack.join("/")
    }

    // Read and Write

    #[pyo3(signature = (key, default=None))]
    pub fn value(&self, py: Python<'_>, key: String, default: Option<Bound<'_, PyAny>>) -> PyResult<Py<PyAny>>{
        let path = self.full_path(&key);
        let mut current = &self.data;

        for step in path {
            if let Some(next) = current.get(step) {
                current = next;
            } else {
                return Ok(default.map(|d| d.unbind()).unwrap_or_else(|| py.None()));
            }
        }

        pythonize(py, current)
            .map(|bound_obj| bound_obj.unbind())
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyTypeError, _>(e.to_string()))
    }

    pub fn set_value(&mut self, key: String, value: Bound<'_, PyAny>) -> PyResult<()> {
        let path = self.full_path(&key);
        let mut current = &mut self.data;

        for step in path.iter().rev().skip(1).rev(){
            current = current.as_object_mut()
                .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyTypeError, _>("Expected object at path"))?
                .entry(step)
                .or_insert(serde_json::json!({}));
        }

        let last_key = path.last().ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Empty key"))?;
        let json_value: serde_json::Value = depythonize(&value)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyTypeError, _>(e.to_string()))?;

        current.as_object_mut().unwrap().insert(last_key.clone(), json_value);
        Ok(())
    }

    pub fn contains(&self, key: String) -> bool {
        let path = self.full_path(&key);
        let mut current = &self.data;
        
        for step in path {
            if let Some(next) = current.get(step) {
                current = next;
            } else {
                return false;
            }
        }
        true
    }

    pub fn remove(&mut self, key: String) -> PyResult<()> {
        let path = self.full_path(&key);
        let mut current = &mut self.data;

        for step in path.iter().rev().skip(1).rev() {
            if let Some(next) = current.get_mut(step) {
                current = next;
            } else {
                return Ok(());
            }
        }

        if let Some(obj) = current.as_object_mut() {
            if let Some(last_key) = path.last() {
                obj.remove(last_key);
            }
        }
        Ok(())
    }

    // Navigations

    pub fn all_keys(&self) -> Vec<String> {
        let mut keys = Vec::new();
        if let Some(node) = self.get_current_node() {
            self.collect_keys_recursive(node, String::new(), &mut keys);
        }
        keys
    }

    pub fn child_keys(&self) -> Vec<String> {
        self.get_current_node()
            .and_then(|n| n.as_object())
            .map(|obj| {
                obj.iter()
                    .filter(|(_, v)| !v.is_object())
                    .map(|(k, _)| k.clone())
                    .collect()
            })
            .unwrap_or_default()
    }

    pub fn child_groups(&self) -> Vec<String> {
        self.get_current_node()
            .and_then(|n| n.as_object())
            .map(|obj| {
                obj.iter()
                    .filter(|(_, v)| v.is_object())
                    .map(|(k, _)| k.clone())
                    .collect()
            })
            .unwrap_or_default()
    }

    // state
    pub fn clear(&mut self) {
        if self.stack.is_empty() {
            self.data = serde_json::json!({});
        } else {
            let mut current = &mut self.data;
            for step in &self.stack {
                if let Some(next) = current.get_mut(step) {
                    current = next;
                } else {
                    return;
                }
            }
            if let Some(obj) = current.as_object_mut() {
                obj.clear();
            }
        }
    }


    pub fn sync(&self, py: Python<'_>) {
        self.driver.save(py, &self.path, &self.data);
    }

    pub fn status(&self) -> i32 {
        0
    }

    pub fn is_writable(&self) -> bool{
        true
    }

    pub fn file_name(&self) -> String{
        self.path.clone()
    }
}

impl LdtSettingEngine {
    fn full_path(&self, key: &str) -> Vec<String>{
        let mut path = self.stack.clone();

        for part in key.split('/'){
            if !part.is_empty() {path.push(part.to_string());}
        }

        path
    }

    fn get_current_node(&self) -> Option<&serde_json::Value> {
        let mut current = &self.data;
        for step in &self.stack {
            current = current.get(step)?;
        }
        Some(current)
    }

    fn collect_keys_recursive(&self, node: &serde_json::Value, prefix: String, acc: &mut Vec<String>) {
        if let Some(obj) = node.as_object() {
            for (k, v) in obj {
                let full_key = if prefix.is_empty() { 
                    k.clone() 
                } else { 
                    format!("{}/{}", prefix, k) 
                };

                if v.is_object() {
                    self.collect_keys_recursive(v, full_key, acc);
                } else {
                    acc.push(full_key);
                }
            }
        }
    }
}