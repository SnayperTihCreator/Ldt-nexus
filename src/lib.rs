use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyString};
use pyo3::{intern, Py, PyAny};

#[pyclass(subclass)]
pub struct NativeLDT {
    #[pyo3(get)]
    data: Py<PyDict>,
    #[pyo3(get, set)]
    readonly: bool,
}

#[pymethods]
impl NativeLDT {
    #[new]
    #[pyo3(signature = (data=None, readonly=false))]
    fn new(py: Python<'_>, data: Option<Py<PyDict>>, readonly: bool) -> PyResult<Self> {
        let data = data.unwrap_or_else(|| PyDict::new(py).unbind());
        Ok(NativeLDT { data, readonly })
    }

    fn get_path(&self, py: Python<'_>, path: &str) -> PyResult<Py<PyAny>> {
        if path.is_empty() {
            return Ok(self.data.clone_ref(py).into_any());
        }
        
        let mut curr = self.data.bind(py).clone();
        for key in path.split('.') {
            match curr.get_item(key)? {
                Some(item) => {
                    // ЗАМЕНА: downcast -> cast
                    if let Ok(d) = item.cast::<PyDict>() {
                        curr = d.clone(); 
                    } else {
                        return Ok(item.clone().into_any().unbind());
                    }
                }
                None => return Ok(py.None()),
            }
        }
        Ok(curr.into_any().unbind())
    }

    fn set_path(&self, py: Python<'_>, path: &str, value: Py<PyAny>) -> PyResult<bool> {
        if self.readonly {
            return Err(pyo3::exceptions::PyPermissionError::new_err("LDT is frozen"));
        }
        let keys: Vec<&str> = path.split('.').collect();
        let mut curr = self.data.bind(py).clone();

        for &key in &keys[..keys.len() - 1] {
            let next_item = curr.get_item(key)?;
            if let Some(item) = next_item {
                // ЗАМЕНА: downcast -> cast
                if let Ok(d) = item.cast::<PyDict>() {
                    curr = d.clone();
                } else {
                    let new_dict = PyDict::new(py);
                    curr.set_item(key, &new_dict)?;
                    curr = new_dict;
                }
            } else {
                let new_dict = PyDict::new(py);
                curr.set_item(key, &new_dict)?;
                curr = new_dict;
            }
        }

        let last_key = keys.last().unwrap();
        curr.set_item(last_key, value)?;
        Ok(true)
    }

    fn serialize_recursive(
        &self,
        py: Python<'_>,
        obj: Py<PyAny>,
        serializers: Bound<'_, PyDict>,
    ) -> PyResult<Py<PyAny>> {
        let obj_bound = obj.bind(py);

        if let Ok(ldt_obj) = obj_bound.downcast::<NativeLDT>() {
            let inner_data = ldt_obj.borrow().data.clone_ref(py);
            return Ok(inner_data.into_any());
        }

        if obj_bound.is_instance_of::<PyString>() ||
           obj_bound.is_instance_of::<pyo3::types::PyInt>() ||
           obj_bound.is_instance_of::<pyo3::types::PyFloat>() ||
           obj_bound.is_instance_of::<pyo3::types::PyBool>() ||
           obj_bound.is_none() {
            return Ok(obj);
        }

        let obj_type = obj_bound.get_type();
        if let Some(ser_func) = serializers.get_item(&obj_type)? {
            let res = ser_func.call1((obj_bound,))?;

            // ЗАМЕНА: downcast -> cast
            if let Ok(res_dict) = res.cast::<PyDict>() {
                let module: String = obj_type.getattr(intern!(py, "__module__"))?.extract()?;
                let name: String = obj_type.getattr(intern!(py, "__name__"))?.extract()?;
                let type_name = format!("{}.{}", module, name);
                res_dict.set_item(intern!(py, "_dtype"), type_name)?;
            }
            return Ok(res.clone().into_any().unbind());
        }

        // ЗАМЕНА: downcast -> cast
        if let Ok(list) = obj_bound.cast::<PyList>() {
            let new_list = PyList::empty(py);
            for item in list.iter() {
                let serialized = self.serialize_recursive(py, item.clone().into_any().unbind(), serializers.clone())?;
                new_list.append(serialized)?;
            }
            return Ok(new_list.into_any().unbind());
        }

        // ЗАМЕНА: downcast -> cast
        if let Ok(dict) = obj_bound.cast::<PyDict>() {
            let new_dict = PyDict::new(py);
            for (k, v) in dict.iter() {
                let serialized = self.serialize_recursive(py, v.clone().into_any().unbind(), serializers.clone())?;
                new_dict.set_item(k, serialized)?;
            }
            return Ok(new_dict.into_any().unbind());
        }

        Ok(obj)
    }

    fn deep_update_py(&self, _py: Python<'_>, target: Bound<'_, PyDict>, source: Bound<'_, PyDict>) -> PyResult<()> {
        self.internal_deep_update(&target, &source)
    }
    
    // ДОПОЛНИТЕЛЬНО: Добавим delete_path для полноты картины
    fn delete_path(&self, py: Python<'_>, path: &str) -> PyResult<()> {
        if self.readonly {
            return Err(pyo3::exceptions::PyPermissionError::new_err("LDT is frozen"));
        }
        let keys: Vec<&str> = path.split('.').collect();
        if keys.is_empty() { return Ok(()); }

        let mut curr = self.data.bind(py).clone();
        for &key in &keys[..keys.len() - 1] {
            if let Some(item) = curr.get_item(key)? {
                if let Ok(d) = item.cast::<PyDict>() {
                    curr = d.clone();
                    continue;
                }
            }
            return Ok(());
        }
        let last_key = keys.last().unwrap();
        curr.del_item(last_key)?;
        Ok(())
    }

    #[pyo3(signature = (path=""))]
    fn list_keys(&self, py: Python<'_>, path: &str) -> PyResult<Vec<String>> {
        let branch = self.get_path_internal(py, path)?;
        let mut keys = Vec::new();

        if let Some(dict) = branch.and_then(|b| b.bind(py).downcast::<PyDict>().ok().cloned()) {
            for (k, v) in dict.iter() {
                // Если значение НЕ словарь - это ключ
                if v.downcast::<PyDict>().is_err() {
                    keys.push(k.extract::<String>()?);
                }
            }
        }
        Ok(keys)
    }

    #[pyo3(signature = (path=""))]
    fn list_groups(&self, py: Python<'_>, path: &str) -> PyResult<Vec<String>> {
        let branch = self.get_path_internal(py, path)?;
        let mut groups = Vec::new();

        if let Some(dict) = branch.and_then(|b| b.bind(py).downcast::<PyDict>().ok().cloned()) {
            for (k, v) in dict.iter() {
                // Если значение словарь - это группа
                if v.downcast::<PyDict>().is_ok() {
                    groups.push(k.extract::<String>()?);
                }
            }
        }
        Ok(groups)
    }

    // Вспомогательный метод (внутренний)
    fn get_path_internal(&self, py: Python<'_>, path: &str) -> PyResult<Option<PyObject>> {
        if path.is_empty() {
            return Ok(Some(self.data.clone_ref(py).into_any()));
        }
        let mut curr = self.data.bind(py).clone();
        for key in path.split('.') {
            if key.is_empty() { continue; }
            match curr.get_item(key)? {
                Some(item) => {
                    if let Ok(d) = item.downcast_into::<PyDict>() {
                        curr = d;
                    } else { return Ok(None); }
                }
                None => return Ok(None),
            }
        }
        Ok(Some(curr.into_any().unbind()))
    }
}

impl NativeLDT {
    fn internal_deep_update(&self, target: &Bound<'_, PyDict>, source: &Bound<'_, PyDict>) -> PyResult<()> {
        for (key, val) in source.iter() {
            // ЗАМЕНА: downcast -> cast
            if let Ok(source_dict) = val.cast::<PyDict>() {
                if let Ok(Some(target_val)) = target.get_item(&key) {
                    // ЗАМЕНА: downcast -> cast
                    if let Ok(target_dict) = target_val.cast::<PyDict>() {
                        self.internal_deep_update(&target_dict, &source_dict)?;
                        continue;
                    }
                }
            }
            target.set_item(key, val)?;
        }
        Ok(())
    }
}

#[pymodule]
fn _ldt(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<NativeLDT>()?;
    Ok(())
}