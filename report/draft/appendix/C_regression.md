This appendix supports the regression reported in Section 2. The cross-section is
eighteen member states holding both measures for 2024: the share of internet
users who purchased online [[ES7]] and e-sales as a share of enterprise turnover
[[ES6]]. All computation is reproducible from `02_MASTER`; the workbook computes
the same statistics as live formulas on sheet `F6_ADOPT_BENEFIT`.

### C.1 The estimate

| Statistic | Value |
|---|---|
| Slope | +0.6022 pp turnover per pp adoption |
| Standard error | 0.1047 |
| t (16 df) | 5.749 |
| 95% confidence interval | [0.380, 0.824] |
| R² | 0.674 |
| Residual standard error (RMSE) | 4.450 pp |
| n | 18 |

The interval is the honest statement of what eighteen observations support. At
the lower bound a percentage point of adoption is worth 0.38pp of turnover; at
the upper bound, 0.82. The point estimate alone would overstate the precision by
a factor of roughly two.

### C.2 Residuals

[[AF_RESID]]

No state is mispredicted by more than two residual standard errors, so the linear
form is not obviously wrong. The largest positive residuals are Belgium (+7.69pp,
+1.73 RMSE), Ireland (+6.31, +1.42) and Italy (+5.51, +1.24).

Denmark's residual is **+4.34pp, or +0.97 RMSE, fourth largest of eighteen**.
This is the figure that killed an earlier version of this report's argument. A
residual inside one standard error, with three states further above the line, is
an ordinary position on the fitted relationship, not evidence that Denmark
converts adoption into commercial activity unusually well. Section 2 says only
that Denmark sits above the line and within one standard error of it.

### C.3 Leave-one-out stability

[[AF_JACK]]

Re-estimating the slope eighteen times, dropping each member state in turn, gives
a range of **[0.516, 0.672]**. The slope never approaches zero and never changes
sign, and every re-estimate falls inside the full-sample confidence interval.
Ireland is the most influential single observation: dropping it moves the slope
by −0.086, about 14%. That is unsurprising, since Ireland is the extreme point on
both axes, and it is the reason Section 2 quotes an interval rather than a point.

### C.4 Selection on the tails, measured

[[AF_TAIL]]

An earlier version of this figure drew its adoption values from a Eurostat news
release [[ES4]], which named nine countries: the three highest, the three lowest
and three notable movers. Six of those nine also report the turnover measure, so
the figure originally rested on six observations drawn entirely from the ends of
the distribution.

| Sample | n | Slope | R² |
|---|---|---|---|
| Six tail countries (press-release values) | 6 | +0.655 | 0.853 |
| All eighteen (databrowser extract) | 18 | +0.602 | 0.674 |

The slope moved by about 8%; the fit fell by 0.18. Selecting on the tails
therefore inflated the apparent explanatory power far more than it biased the
estimated relationship, which is the characteristic signature of range
restriction in reverse, and a demonstration of selection bias measured on this
report's own data rather than asserted from a textbook.

One detail matters for anyone reproducing this. The tail-sample statistics are
computed from the **rounded values the press release printed** (Ireland 96,
Denmark 91, Germany 83, Hungary 79, Italy 60, Bulgaria 57), because the point is
what the earlier figure actually showed. Recomputing the same six countries from
the databrowser's unrounded values gives a slope of 0.658 and R² of 0.854: the
same conclusion, marginally different digits.

### C.5 Is the missing third of the EU missing for a reason?

Nine member states report adoption but not turnover: EE, EL, FI, LT, LV, NL, PT,
RO and SK. If they were absent because of something correlated with the outcome,
the estimate would be selected rather than merely incomplete.

They average **75.67%** on adoption against the plotted eighteen's **77.23%**, a
difference of −1.57pp, with a two-sample t of −0.372 on 25 degrees of freedom,
p ≈ 0.71. The two groups are statistically indistinguishable on the x-axis. The
sample is missing on availability of the outcome measure, not selected on the
regressor.

That test has a limit worth stating, because it is the strongest objection to this
section. Balance on the regressor is not balance on the outcome, and the reasons a
national statistical institute fails to publish an e-sales turnover figure are not
all random with respect to economic structure. Eurostat requires turnover at basic
prices excluding VAT, and rejects national submissions failing coherence checks
against Structural Business Statistics. Web and EDI sales behave differently, since
EDI carries industrial business-to-business volume, so a small change in which
large manufacturers fall into the sample can move a national share by several
points. And secondary suppression removes a national total outright where one or
two dominant firms in a NACE division would let their figure be recovered by
subtraction. That last mechanism is the troubling one: it makes missingness a
function of market concentration, which is plausibly related to enterprise
e-commerce intensity. A balance test on consumer adoption cannot detect it. The
honest statement is that the nine are missing for administrative and disclosure
reasons rather than for anything this section could observe, which is weaker than
missing at random and stronger than selected on the outcome.

### C.6 What this design still cannot do

Adoption is measured on consumers and turnover on enterprises, including
business-to-business ordering no consumer ever touches, so the two axes are not
two sides of one transaction. National income appears on neither axis and would
plausibly raise both. Both are single-year cross-sections, so nothing here
identifies a direction of causation. The relationship is an association that
survives every robustness check available on eighteen observations, and that is
the whole of the claim.
