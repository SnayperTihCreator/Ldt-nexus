use pyo3_stub_gen::Result;

fn main() -> Result<()>{
    let stub = _ldt_core::stub_info()?;
    stub.generate()?;
    print!("Succes generate");
    Ok(())
}