# Evaluation of Databricks and Workflow Alternatives

## Databricks Overview

Databricks is a data platform built on top of **Apache Spark**.

Apache Spark processes data using a **cluster-based architecture**, meaning multiple machines (nodes) work together at the same time. Because of this distributed computing approach, infrastructure cost can become relatively high compared to simpler execution methods.

---

## Why Databricks May Not Fit Our Current Use Case

Current requirement:

* Run Python code
* Call external APIs
* Execute scheduled workloads
* Keep infrastructure cost low

### Observations

### 1. Higher Infrastructure Cost

Databricks workloads run on Spark clusters.

Even for smaller jobs, clusters may need to start and remain active, which increases cost compared to lightweight serverless solutions.

---

### 2. Limited External API Access in Free Edition

The Databricks Free Edition currently has limitations regarding outbound internet connectivity.

As a result:

* External API calls may not be available
* Difficult to use for API-driven workflows

---

### 3. Designed for Large-Scale Data Processing

Databricks becomes useful when handling:

* Very large datasets (GB,TB,PB scale)
* Distributed analytics
* Real-time streaming pipelines
* Complex data engineering workloads

Example use case:

* Credit card fraud detection where live data must be processed instantly across multiple systems.

For simple API execution and scheduled automation, Databricks may be over-engineered.

---

## Free Tier Notes

Databricks Free Tier currently provides:

* Approximately **400 credits**
* Limited compute resources
* **2x-small warehouse**
* Around **5 concurrent tasks**
* Credits remain valid for **14 days**
* Subscription required afterward for continued usage

---

# Alternative Workflow Options

## Option 1 — Amazon EventBridge

### Description

EventBridge is a lightweight event scheduler.

### Advantages

* Simple scheduling
* Low operational overhead
* Good for running periodic jobs

### Limitations

* Limited execution visibility
* No built-in retry workflow
* Does not manage execution state

Best for:

* Simple scheduled triggers

---

## Option 2 — AWS Step Functions (Recommended)

### Description

AWS Step Functions is a serverless workflow orchestration service.

### Advantages

* Built-in error handling
* Automatic retry logic
* State management
* Workflow visibility
* Better monitoring

### Pricing

* Around **40,000 state transitions/month free**
* For this use case, expected monthly cost is **close to $0**

Best for:

* API execution workflows
* Scheduled tasks with monitoring
* Production-ready orchestration

---

# Final Recommendation
Reason:
Databricks is optimized for large-scale distributed data processing rather than lightweight API-based workloads.
