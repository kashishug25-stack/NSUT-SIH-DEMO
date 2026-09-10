# Data Required From User

This file lists the external official data needed to complete the remaining SIH requirements. The current scraper and database do not need to be changed for these steps.

## Already Completed Without External Data

The prototype currently has:

- Existing SQLite quote database
- Cleartrip, EaseMyTrip, and Yatra stored observations
- 8 configured routes
- T+1, T+7, T+15, T+30, T+45 horizons
- Economy cabin scope
- Route intelligence page
- All-route market overview page
- Source health page
- Provisional Laspeyres airfare index

Source health page:

```text
http://127.0.0.1:8000/source-health.html
```

The home screen does not currently show a source-health button. It is a separate page until navigation is added deliberately.

---

## 1. DGCA Traffic Data For Route Weights

### Why It Is Needed

The current index uses provisional equal route weights. The problem statement expects a representative basket based on traffic importance.

The preferred route-weight formula is:

```text
route_weight = route_passengers / total_passengers_in_selected_basket
```

### Where To Search

1. Open:

```text
https://www.dgca.gov.in/
```

2. Search the website for:

```text
Domestic passenger traffic route wise
Airport wise passenger traffic
Domestic air traffic statistics
Passenger traffic monthly data
```

3. Also search:

```text
https://data.gov.in/
```

Search terms:

```text
DGCA domestic passenger traffic
airport-wise passenger traffic India
route-wise air passenger traffic India
```

### What To Download

Prefer an official CSV or XLS file. PDF is acceptable if no structured file exists.

The file should contain one of these:

- Route and passenger count, or
- Origin/destination airports and passenger count, or
- Airport passenger traffic with a documented proxy method

### Required Fields

Ideal structured columns:

```text
origin
 destination
 passengers
 reference_period
```

The exact names may differ. Keep the original file unchanged.

### Where To Put It

Create this folder if necessary:

```text
data/government/
```

Copy the downloaded file there, for example:

```text
data/government/dgca_traffic_2025.csv
```

Also create a small text note beside it:

```text
data/government/dgca_traffic_2025_source.txt
```

Put these details in the note:

```text
Dataset title:
Official publisher:
Source URL:
Download date:
Reference period:
Units:
Column meanings:
Any airport-to-city mapping used:
Any proxy assumption:
```

Do not manually type passenger values into the application.

---

## 2. MoSPI CPI Data For Comparison

### Why It Is Needed

The airfare index can be compared with an official CPI series only after obtaining the exact official series, base year, classification, and monthly values.

Do not label a broad transport index as airfare CPI unless the official metadata confirms that classification.

### Where To Search

1. Open:

```text
https://www.mospi.gov.in/
```

2. Search for:

```text
Consumer Price Index time series
CPI Transport and Communication
CPI passenger transport by air
CPI air transport
```

3. Also search:

```text
https://data.gov.in/
```

Search terms:

```text
MoSPI CPI transport communication
CPI air transport India
Consumer Price Index passenger transport by air
```

### What To Download

Prefer an official CSV, XLS, or API response containing monthly values.

The file must identify:

- Month
- CPI value
- Series name
- Base year
- Rural/urban/combined category, if applicable
- Frequency

### Required Fields

Ideal structured columns:

```text
month
cpi_value
series_name
base_year
frequency
```

The exact names may differ. Keep the original official file unchanged.

### Where To Put It

Copy the file to:

```text
data/government/mospi_cpi_reference.csv
```

If the official file is XLS, keep the original too:

```text
data/government/mospi_cpi_reference.xlsx
```

Create a source note:

```text
data/government/mospi_cpi_reference_source.txt
```

Use this template:

```text
Dataset title:
Official publisher:
Source URL:
Download date:
Reference period covered:
Series name:
CPI classification:
Base year:
Frequency:
Units/index meaning:
Rural/urban/combined:
```

---

## 3. What To Send Back

After downloading, provide either:

1. The files placed inside `data/government/`, or
2. The exact downloaded filenames and source URLs.

Do not rename columns or edit values before providing the files.

The next implementation can then:

- Parse the official DGCA file
- Calculate documented route weights
- Replace provisional equal weights
- Parse the MoSPI CPI series
- Rebase APIx and CPI to the same month
- Build the CPI comparison page
- Show monthly inflation and year-on-year changes

---

## 4. Formulas To Be Used Later

### Traffic Route Weight

```text
w_i = passengers_i / sum(passengers in selected basket)
```

### Laspeyres Airfare Index

```text
APIx_t = 100 * sum(w_i * (P_i,t / P_i,0)) / sum(w_i)
```

### Monthly Airfare Index

```text
monthly_APIx_m = average(daily_APIx values in month m)
```

### Monthly Inflation

```text
inflation_m = 100 * (APIx_m - APIx_(m-1)) / APIx_(m-1)
```

### Year-on-Year Change

```text
YoY_m = 100 * (APIx_m - APIx_(m-12)) / APIx_(m-12)
```

### Rebased Comparison

```text
rebased_series_t = 100 * series_t / series_base_month
```

Both APIx and CPI must be rebased to the same comparison month before charting them together.

---

## 5. Important Accuracy Rules

- Use only official government files for government comparisons.
- Preserve the original downloaded files.
- Record source URLs and reference periods.
- Do not invent missing values.
- Do not treat provisional equal weights as official weights.
- Do not call APIx official CPI.
- If the official CPI series is a proxy, label it as a proxy.
- Do not modify scraper files while integrating reference data.
