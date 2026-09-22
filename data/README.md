# APS-02 Data Layer

This folder houses the SQLite database (`APS-02.db`) and helper initialization scripts for the Jett 2 Holiday platform.

## Database Location
- **Path**: `data/APS-02.db`

## Key Tables in APS-02.db
As outlined in the APS-02 Problem Statement & Design Document, the schema comprises:
- `pricing_events`: Primary event telemetry (searches, views, bookings, cancellations, abandonments) with timestamp and lead time.
- `inventory_calendar`: Entity-by-date room/seat availability, capacity, and booked units.
- `price_bounds`: Floor price, ceiling price, max daily move pct, and rounding step rules.
- `price_history`: Log of calculated dynamic prices, demand indices, factor contributions, and clamping state.
- `hotels`: Hotel property metadata, star rating, city mappings.
- `flights` & `flight_fares`: Flight routes, schedules, cabin classes, and benchmark base fares.
- `cities`: Destination city profiles, peak months, and seasonal weights.
- `currencies` & `languages`: Currency symbols, minor unit precision, and BCP-47 locale tags (`en-IN`, `hi`).
- `simulations`: Stored what-if scenario runs and projected revenue parameters.

## Initialization Helper
If `APS-02.db` is not present, you can run:
```bash
python init_db.py
```
This will create a lightweight skeleton database with the required tables so local development and ML scripts can execute without errors.
