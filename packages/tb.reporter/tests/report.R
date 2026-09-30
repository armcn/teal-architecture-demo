stopifnot(identical(tb.reporter::report_text(c(2, 4)),
                    "Observations: 2 | Mean: 3.00 | Range: 2.00 to 4.00"))
stopifnot(identical(tb.reporter::report_text(c(-2, -2)),
                    "Observations: 2 | Mean: -2.00 | Range: -2.00 to -2.00"))
