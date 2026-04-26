# Idempotency in Training API

## Overview

The `/train` endpoint implements **idempotency** to prevent duplicate job creation when the same request is sent multiple times. This is especially important in distributed systems where retries may occur due to timeouts, network issues, or client-side failures.

Idempotency is achieved using a **client-provided identifier (`client_id`)**, which acts as a unique key for each logical training request.


## Endpoint

POST /train

## Query Parameters

| Parameter      | Type    | Required | Description |
|----------------|---------|----------|-------------|
| client_id      | string  | yes      | Unique identifier for the request (idempotency key) |
| dataset_name   | string  | yes      | Name of the dataset |
| dataset_id     | integer | yes      | Dataset identifier |

## Behavior

The endpoint guarantees the following behavior:

- **New `client_id`**
  - A new training job is created
  - A new `job_id` is returned

- **Existing `client_id`**
  - No new job is created
  - The previously created `job_id` is returned

This ensures that repeated requests with the same parameters and `client_id` will not create duplicate jobs.


## Example

### First Request

```

POST /train?client_id=abc123&dataset_name=test_dataset&dataset_id=1

````

Response:

```json
{
  "job_id": 42,
  "status": "pending"
}
```

### Retry (Same Request)

```
POST /train?client_id=abc123&dataset_name=test_dataset&dataset_id=1
```

Response:

```json
{
  "job_id": 42,
  "status": "pending"
}
```

## Implementation Details

Idempotency is enforced at the database level using a unique constraint:

```sql
ALTER TABLE jobs ADD CONSTRAINT unique_client_id UNIQUE (client_id);
```

Request handling logic:

1. Check for an existing job:

   ```sql
   SELECT job_id FROM jobs WHERE client_id = $1;
   ```

2. If found → return existing `job_id`

3. If not found → create new job:

   ```sql
   INSERT INTO jobs (client_id, dataset_name, dataset_id, status)
   VALUES ($1, $2, $3, 'pending')
   RETURNING job_id;
   ```

## Failure Scenarios

| Scenario                       | Behavior                            |
| ------------------------------ | ----------------------------------- |
| Duplicate request              | Returns existing job                |
| Database failure during insert | Safe to retry with same `client_id` |
| Missing `client_id`            | Returns `422 Unprocessable Entity`  |
| Invalid parameters             | Returns `422 Unprocessable Entity`  |

## Best Practices

* Use a **UUID** for `client_id`
* Generate a new `client_id` for each logical training request
* Reuse the same `client_id` only when retrying the same request
* Do not reuse `client_id` across unrelated requests

## Summary

By introducing `client_id` as an idempotency key, the `/train` endpoint ensures:

* No duplicate job creation
* Safe retries
* Consistent API behavior under failure conditions
* Improved reliability in distributed environments