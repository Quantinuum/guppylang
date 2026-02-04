use miette::{Diagnostic, GraphicalReportHandler, LabeledSpan, Severity};
use pyo3::prelude::*;
use std::fmt;

#[pyclass]
#[derive(Clone, Debug)]
struct PyDiagnostic {
    message: String,
    code: Option<String>,
    severity: String,
    source: Option<String>,
    spans: Vec<(usize, usize, Option<String>)>,
    help_text: Option<String>,
}

#[pymethods]
impl PyDiagnostic {
    #[new]
    fn new(
        message: String,
        code: Option<String>,
        severity: String,
        source: Option<String>,
        spans: Vec<(usize, usize, Option<String>)>,
        help_text: Option<String>,
    ) -> Self {
        Self {
            message,
            code,
            severity,
            source,
            spans,
            help_text,
        }
    }
}

impl fmt::Display for PyDiagnostic {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for PyDiagnostic {}

impl Diagnostic for PyDiagnostic {
    fn code<'a>(&'a self) -> Option<Box<dyn fmt::Display + 'a>> {
        self.code
            .as_ref()
            .map(|c| Box::new(c) as Box<dyn fmt::Display>)
    }

    fn severity(&self) -> Option<Severity> {
        match self.severity.as_str() {
            "error" => Some(Severity::Error),
            "warning" => Some(Severity::Warning),
            "note" | "help" | "advice" => Some(Severity::Advice),
            _ => Some(Severity::Error),
        }
    }

    fn source_code(&self) -> Option<&dyn miette::SourceCode> {
        self.source.as_ref().map(|s| s as &dyn miette::SourceCode)
    }

    fn labels(&self) -> Option<Box<dyn Iterator<Item = LabeledSpan> + '_>> {
        if self.spans.is_empty() {
            None
        } else {
            Some(Box::new(self.spans.iter().map(|(start, len, label)| {
                LabeledSpan::new(label.clone(), *start, *len)
            })))
        }
    }

    fn help<'a>(&'a self) -> Option<Box<dyn fmt::Display + 'a>> {
        self.help_text
            .as_ref()
            .map(|h| Box::new(h) as Box<dyn fmt::Display>)
    }
}

#[pyfunction]
fn render_report(diagnostic: PyDiagnostic) -> PyResult<String> {
    let handler = GraphicalReportHandler::new();

    let mut output = String::new();
    handler
        .render_report(&mut output, &diagnostic as &dyn Diagnostic)
        .map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Failed to render: {}", e))
        })?;

    Ok(output)
}

#[pyfunction]
fn guppy_to_miette(
    title: String,
    level: String,
    source_text: Option<String>,
    spans: Vec<(usize, usize, Option<String>)>,
    message: Option<String>,
    help_text: Option<String>,
) -> PyDiagnostic {
    PyDiagnostic::new(
        message.unwrap_or(title),
        None,
        level,
        source_text,
        spans,
        help_text,
    )
}

#[pymodule]
fn miette_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDiagnostic>()?;
    m.add_function(wrap_pyfunction!(render_report, m)?)?;
    m.add_function(wrap_pyfunction!(guppy_to_miette, m)?)?;
    Ok(())
}
