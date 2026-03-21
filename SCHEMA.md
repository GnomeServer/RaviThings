# DOE Contracts Datastore Schema

This datastore contains US Department of Energy contract transaction data from FY2007 to FY2026.

## SQLite Database: `doe_contracts.db`
**Table Name:** `contracts`

| Column | Type | Description |
|--------|------|-------------|
| `contract_transaction_unique_key` | TEXT | Primary Key for the transaction |
| `award_id_piid` | TEXT | The unique ID for the overall award |
| `action_date` | DATETIME | When the transaction occurred |
| `action_date_fiscal_year` | INTEGER | The Fiscal Year (2007-2026) |
| `federal_action_obligation` | REAL | The dollar amount of this specific transaction |
| `total_dollars_obligated` | REAL | Total dollars on the award to date |
| `awarding_agency_name` | TEXT | Usually "Department of Energy" |
| `recipient_name` | TEXT | The company/entity receiving the money |
| `recipient_state_name` | TEXT | State where the company is located |
| `transaction_description` | TEXT | **CRITICAL**: Description of what the money is for |
| `award_type` | TEXT | e.g., "BPA CALL", "DELIVERY ORDER", "CONTRACT" |

## Vector Store: `chroma_db/`
**Collection Name:** `doe_contracts`
Use this for semantic searches like "find battery research" or "clean energy startups".

## Python Integration
Use `from datastore_gateway import ContractDataStore` to initialize the connection.
