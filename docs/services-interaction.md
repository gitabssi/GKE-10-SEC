# Services Interaction Graph

Below is the high-level interaction graph of Bank of Anthos with the external AI Fraud Detection components used for the hackathon demo.

```mermaid
graph LR
  %% Bank of Anthos core
  subgraph Bank_of_Anthos
    UA[User Browser]
    FE[frontend]
    LW[ledgerwriter]
    BR[balancereader]
    TH[transactionhistory]
    LDB[(ledger-db)]

    UA -->|HTTP| FE
    FE -->|Reads| BR
    FE -->|Reads| TH
    BR -->|SQL| LDB
    TH -->|SQL| LDB
  end

  %% Interception via config
  CM[(service-api-config\nConfigMap)]
  FE -. TRANSACTIONS_API_ADDR .-> CM
  CM -. redirects --> TI

  %% Fraud detection stack
  subgraph Fraud_Detection
    TI[transaction-interceptor]
    FAPI[fraud-api (FastAPI)]
    FDB[(fraud-db)]
    FDASH[fraud-dashboard]
  end

  %% External AI
  GAI[(Gemini API)]

  %% Flows
  FE -->|Create Txn| TI
  TI -->|Forward original txn| LW
  LW -->|Write| LDB

  TI -->|Analyze(txn)| FAPI
  FAPI -->|LLM call| GAI
  FAPI -->|Store results| FDB
  FAPI -->|Webhook: analyzed txn| FDASH
  FDASH -->|Query/Health| FAPI

  %% Optional demo tooling
  subgraph Demo_Control
    DCTRL[demo-control]
    LG[loadgenerator]
  end
  DCTRL --> LG
  DCTRL --> FDASH

  %% Notes
  note right of CM: Redefines frontend\nTRANSACTIONS_API_ADDR\nto point to interceptor
  note bottom of FAPI: Exposes /analyze-bank-transaction\n+ /transactions + /health
  note bottom of FDASH: Receives webhook /api/transaction-analyzed\nDisplays real-time analysis
```

Notes:
- All external URLs/IPs are parameterized via environment variables for security. Replace placeholders (e.g., YOUR_BANK_OF_ANTHOS_URL) during deployment.
- The interceptor is transparent to core Bank of Anthos services and forwards transactions to ledgerwriter after capturing and analyzing.

