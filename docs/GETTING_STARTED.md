# Getting started - no programming needed

This page assumes you have never used a command line. Everything here is
double-clicking files and dragging things onto them.

If you are comfortable with a terminal, skip to
[WORKFLOW.md](WORKFLOW.md) instead.

---

## What you need once

**Python.** Download it from <https://www.python.org/downloads/> and run the
installer.

> **The one thing that matters:** on the first screen of the installer, tick
> **"Add python.exe to PATH"** at the bottom before you click Install. If you
> miss it, uninstall Python and run the installer again.

**The tool itself.** Download the project from GitHub:

1. Go to <https://github.com/Vighnesh-Industrial/DFX-Analysis-Suite>
2. Click the green **Code** button, then **Download ZIP**
3. Right-click the downloaded ZIP, choose **Extract All**, and put it
   somewhere easy such as `Documents\DFX`

You should end up with a folder containing `run_analysis.bat`,
`run_dashboard.bat`, `analyze.py` and some others.

---

## Step 1 - Check it works

Find **`run_analysis.bat`** in that folder and **double-click it**.

A black window opens, some text scrolls past, and then your browser opens
showing a report with pictures of a sample bracket.

That is the whole tool working. Nothing was installed.

> **If a black window flashes and disappears**, Python is not installed or the
> PATH box was not ticked. Reinstall Python, ticking that box.

Two files appear next to `run_analysis.bat`:

* `DFX_Report.html` - the one to read
* `DFX_Report.txt` - the same content as plain text

---

## Step 2 - Get your own part out of your CAD system

The tool cannot read Creo `.prt` or SolidWorks `.sldprt` files. Nothing can,
except the software that made them. So export first.

**In Creo:**

1. Open your part
2. **File > Save As > Save a Copy**
3. Change **Type** to **STEP (\*.stp)**
4. Click **OK**, and in the options that appear choose **AP214** and tick
   **Solids**
5. Save it somewhere easy, for example `Documents\DFX\myparts\`

**Do it a second time, choosing STL instead of STEP.** Set **Chord Height** to
`0.05`. Save it in the same folder **with the same name**:

```
myparts\bracket.stp
myparts\bracket.stl
```

The STL is what lets the tool measure wall thickness and draw solid pictures.
It is worth the extra ten seconds.

> SolidWorks, NX, Inventor and Fusion all have the same two exports under
> **File > Save As** or **File > Export**. Choose **STEP AP214**, then **STL**
> at a fine setting.

---

## Step 3 - Analyse your part

**Drag your `.stp` file and drop it onto `run_analysis.bat`.**

That is it. The black window shows the progress, your browser opens with the
report for your part, and it finds the matching `.stl` next to it on its own.

For an **assembly**, export the whole assembly as one STEP file and drop that
on in exactly the same way. The report gets an extra **Components** table and
every finding says which component it came from.

---

## Step 4 - Read the report

The report opens in your browser. Read it in this order:

1. **The coloured boxes at the top** - five scores out of 10. The first is the
   overall one.
2. **The pictures** - four views of your part. Check they look like the part
   you meant to send. If they do not, the wrong file got exported.
3. **Measured geometry** - the numbers read out of your file: size, hole
   diameters, wall thickness, draft angle.
4. **The findings** - what to fix.

Findings are labelled:

| Label | Meaning |
|---|---|
| **FAIL** | A real problem. Fix it. |
| **CRIT** | The feature cannot be measured by inspection. |
| **WARN** | Costs time or money, but it will work. |
| **INFO** | A check that ran and **passed** - shown so you know it ran. |
| **NOTE** | Something about the file, not the design. |

> **One thing to understand.** An empty list does not mean the part is
> perfect. It means nothing was found *by the checks that could be run*. If
> your export had no solid geometry in it, two of the scores show **n/a**
> rather than a good mark, on purpose.

---

## Step 5 - Save it as a PDF

With the report open in your browser, press **Ctrl + P**, then choose
**Save as PDF** as the printer, and Save.

---

## Step 6 - Tell it how you are making the part

By default the tool applies general rules. If you tell it the process, it
applies that process's rules and finds more:

* **Machined** - checks small holes and internal corner radii
* **Moulded plastic** - checks draft angle, wall thickness and fillets
* **Sheet metal** - checks holes and bends against the sheet thickness
* **3D printed** - measures how much of the surface needs support

The easiest way to choose is the dashboard, in Step 7. From the black window
it is:

```
run_analysis.bat "C:\Documents\DFX\myparts\bracket.stp"
```

...but the dashboard has a dropdown, which is easier.

---

## Step 7 - The upload dashboard (optional)

If you would rather upload files in a browser than drag them onto a `.bat`:

1. Double-click **`setup.bat`** once. It takes a few minutes and prints
   `=== Setup complete ===` at the end.
2. Double-click **`run_dashboard.bat`**. Your browser opens automatically.
3. Choose your `.stp` file, add the matching `.stl` in the second box, pick
   the process from the dropdown, and click **ANALYZE**.
4. Leave the black window open while you use it. Press **Ctrl + C** in it when
   you are finished.

---

## When something goes wrong

| What you see | What to do |
|---|---|
| The window flashes and closes | Python is not on PATH. Reinstall Python and tick **Add python.exe to PATH** |
| `closed vendor format` | You dropped a `.prt` or `.sldprt`. Export to STEP first (Step 2) |
| `none measurable from this file` | The STEP export had no solid in it. Export again with **Solids** ticked |
| Two scores show `n/a` | Nothing could be measured, so nothing was checked. Fix the export - do not read this as a pass |
| No wall thickness in the report | No `.stl` next to the `.stp`. Export one (Step 2) |
| `pip is not recognized` | Run `setup.bat` rather than typing pip commands |
| The dashboard will not start | Run `setup.bat` first |

Still stuck? Open an issue on the GitHub page with the message from the black
window, and the CAD system you exported from.
