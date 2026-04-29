use pyo3::prelude::*;
use pyo3_stub_gen::define_stub_info_gatherer;

mod drivers;
mod engine;

use engine::LdtSettingEngine;

#[pymodule]
mod _ldt_core {

    #[pymodule_export]
    use super::LdtSettingEngine;

}

define_stub_info_gatherer!(stub_info);