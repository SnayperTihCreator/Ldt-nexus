use pyo3::{exceptions::*, prelude::*};
use pyo3_stub_gen::derive::*;
use serde_json::Value;
use pythonize::{depythonize, pythonize};
use std::sync::RwLock;

use crate::drivers::Drivers;


#[gen_stub_pyclass]
#[pyclass]
pub struct LdtSettingEngine {
    #[pyo3(get)]
    pub path: String,

    data: RwLock<Value>,
    stack: RwLock<Vec<String>>,
    driver: Drivers,
}

#[gen_stub_pymethods]
#[pymethods]
impl LdtSettingEngine {

    #[new]
    #[pyo3(signature = (path, driver=None))]
    pub fn new(py: Python<'_>,  path: String, driver: Option<Bound<'_, PyAny>>) -> PyResult<Self>{
        let driver_enum = match driver {
            Some(obj) => Drivers::from_args(obj)?,
            None => Drivers::Json,
        };

        let data = RwLock::new(driver_enum.load(py, &path)?);

        Ok(Self { path, data, stack: RwLock::new(Vec::new()), driver: driver_enum })

    }

    // Group

    pub fn begin_group(&mut self, name: String){
        let clean_name = name.trim_matches('/');
        if !clean_name.is_empty() {
            let mut stask = self.stack.write().unwrap();
            stask.push(clean_name.to_string());
        }
    }

    pub fn end_group(&mut self){
        let mut stack = self.stack.write().unwrap();
        stack.pop();
    }

    pub fn group(&self) -> String {
        let stack = self.stack.read().unwrap();
        stack.join("/")
    }

    // Read and Write

    pub fn contains(&self, key: String) -> bool {
        self.with_node(&key, |_| ()).is_some()
    }

    #[pyo3(signature = (key))]
    pub fn value(&self, py: Python<'_>, key: String) -> PyResult<Py<PyAny>> {
        let res = self.with_node(&key, |val| pythonize(py, val));

        match res {
            Some(Ok(obj)) => Ok(obj.unbind()),
            Some(Err(e)) => Err(PyTypeError::new_err(e.to_string())),
            None => Ok(py.None()),
        }
    }

    pub fn set_value(&self, key: String, value: Bound<'_, PyAny>) -> PyResult<()> {
        let json_value = depythonize(&value)
            .map_err(|e| PyTypeError::new_err(e.to_string()))?;

        self.with_node_mut(&key, |parent_obj, last_key| {
            parent_obj.insert(last_key, json_value);
        })?;
        Ok(())
    }

    pub fn remove(&self, key: String) -> PyResult<()> {
        self.with_node_mut(&key, |parent_obj, last_key| {
            parent_obj.remove(&last_key);
        })
    }

    // Navigations

    pub fn all_keys(&self) -> Vec<String> {
            let mut keys = Vec::new();
            self.with_node("", |node| {
                self.collect_keys_recursive(node, String::new(), &mut keys);
            });
            keys
    }

    pub fn child_keys(&self) -> Vec<String> {
        self.with_node("", |node| {
            node.as_object()
                .map(|obj| {
                    obj.iter()
                        .filter(|(_, v)| !v.is_object())
                        .map(|(k, _)| k.clone())
                        .collect()
                })
                .unwrap_or_default()
        }).unwrap_or_default()
    }

    pub fn child_groups(&self) -> Vec<String> {
        self.with_node("", |node| {
            node.as_object()
                .map(|obj| {
                    obj.iter()
                        .filter(|(_, v)| v.is_object())
                        .map(|(k, _)| k.clone())
                        .collect()
                })
                .unwrap_or_default()
        }).unwrap_or_default()
    }

    // state
    pub fn clear(&self) -> PyResult<()> {
        let mut data = self.data.write().unwrap();
        let stack = self.stack.read().unwrap();
        
        let mut current = data.as_object_mut().unwrap();
        for step in stack.iter() {
            current = current.entry(step).or_insert_with(|| serde_json::json!({})).as_object_mut().unwrap();
        }
        
        current.clear();
        Ok(())
    }


    pub fn sync(&self, py: Python<'_>) -> PyResult<()> {
        let data = self.data.read().unwrap();
        self.driver.save(py, &self.path, &*data)
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
    fn with_node<R, F>(&self, key: &str, f: F) -> Option<R>
    where
        F: FnOnce(&Value) -> R,
    {
        let data = self.data.read().unwrap();
        let stack = self.stack.read().unwrap();

        let mut current = &*data;
        // Идем по стеку групп
        for step in stack.iter() {
            current = current.get(step)?;
        }
        // Идем по ключу
        for part in key.split('/').filter(|s| !s.is_empty()) {
            current = current.get(part)?;
        }
        
        Some(f(current))
    }

    fn with_node_mut<R, F>(&self, key: &str, f: F) -> PyResult<R>
    where
        F: FnOnce(&mut serde_json::Map<String, serde_json::Value>, String) -> R,
    {
        let full_path = {
            let stack = self.stack.read().unwrap();
            let mut p = stack.clone(); // Копируем маленькие строки, это дешево
            for part in key.split('/').filter(|s| !s.is_empty()) {
                p.push(part.to_string());
            }
            p
        };

        let mut parts = full_path;
        let last_key = parts.pop().ok_or_else(|| PyKeyError::new_err("Key is empty"))?;

        let mut data = self.data.write().unwrap();

        let mut current = data.as_object_mut().ok_or_else(|| {
            PyTypeError::new_err("Root is not an object")
        })?;

        for step in parts {
            let next_node = current
                .entry(step)
                .or_insert_with(|| serde_json::Value::Object(serde_json::Map::new()));
            
            current = next_node.as_object_mut().ok_or_else(|| {
                PyTypeError::new_err("Path segment is not an object")
            })?;
        }

        Ok(f(current, last_key))
    }



    fn collect_keys_recursive(&self, node: &Value, prefix: String, acc: &mut Vec<String>) {
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