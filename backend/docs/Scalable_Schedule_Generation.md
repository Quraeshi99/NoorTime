# Architecture Document: Scalable Schedule Generation

## 1. Overview

This document outlines the architecture for the proactive, scalable generation of user prayer-time schedules. The primary challenge with generating schedules for millions of users is avoiding massive, predictable load spikes on the server (e.g., at the end of every month). The chosen architecture, **"Rolling Wave Generation,"** is designed to distribute this workload evenly over time, ensuring system stability, responsiveness, and cost-efficiency.

## 2. Current Architecture: The "Rolling Wave Generation" Model

The current implementation, running on the application's primary VM, uses a combination of a task scheduler (Celery Beat) and a distributed task queue (Celery) to achieve even load distribution.

### 2.1. Core Principles

- **Distribute the Workload:** Instead of a single, massive job at the end of the month, the work of generating next-month schedules is spread out over many days.
- **Process in Parallel:** The total work for a given day is broken down into thousands of tiny, independent tasks that can be executed in parallel by multiple worker processes.
- **Be Configurable:** All key parameters of the system are flexible and can be configured via environment variables without changing the code.

### 2.2. Implementation Details

#### a. Staggered Generation (The "Modulo" Approach)

The foundation of the rolling wave is to assign each user a deterministic "generation day" of the month.

- **Mechanism:** We use the modulo operator (`%`) on the user's primary key (`user.id`).
- **Logic:** A master task runs daily. On any given day `D` of the month, it only processes users for whom `user.id % N == (D-1)`, where `N` is the total number of days the workload is spread across.
- **Example:** If `N=28`, on Day 1 of the month, only users with `id % 28 == 0` are processed. On Day 2, users with `id % 28 == 1` are processed, and so on.

#### b. Master-Worker Task Model

The logic is implemented using two distinct Celery tasks in `project/tasks.py`:

1.  **`master_schedule_generator` (The "Master"):**
    - **Schedule:** This task is run once every day by Celery Beat. Its schedule is configured in `project/celery_utils.py`.
    - **Function:**
        1.  It determines the current day of the month to identify the target user "bucket" (based on the modulo logic).
        2.  It queries the database for all users who belong to that bucket and who do not already have a schedule generated for the upcoming month.
        3.  It does **not** perform the generation itself. Instead, it dispatches thousands of `generate_schedule_for_single_user` tasks to the queue, one for each user.

2.  **`generate_schedule_for_single_user` (The "Worker"):**
    - **Function:** This is a small, atomic task that does one thing: it generates and caches the monthly schedule for a single `user_id`. It contains all the core logic from the `schedule_service`.
    - **Benefit:** Because this task is small and independent, we can run hundreds or thousands of them in parallel across multiple Celery worker processes, maximizing CPU usage.

#### c. User Activity Tracking for Future Prioritization

To enable more advanced, priority-based generation in the future, the system now tracks user activity.

- **Mechanism:** The `User` model in `project/models.py` now has a `last_seen_at` field.
- **Update Logic:** This timestamp is automatically updated in `project/utils/auth.py` every time a user makes a valid, authenticated request to the API.
- **Future Use:** While the current implementation primarily uses the modulo approach, this `last_seen_at` data will allow us to implement "Tiered Generation" (e.g., generating schedules for active users earlier in the month than for inactive users).

### 2.3. Configuration

The entire system is configurable via `project/config.py` (and corresponding environment variables):

- `SCHEDULE_GENERATION_DAYS`: The number of days to spread the workload across (the `N` in our modulo logic).
- `MASTER_SCHEDULER_CRON_HOUR`: The UTC hour for the master task to run.
- `MASTER_SCHEDULER_CRON_MINUTE`: The UTC minute for the master task to run.
- `USER_PRIORITY_BUCKETS_DAYS`: A JSON object to define the time windows for user activity tiers (for future use).

## 3. Future Architecture: Scaling with Kubernetes

The current architecture is designed to be highly efficient on one or a few VMs. When the application's user base grows to a scale that exceeds the capacity of this initial setup, the next logical step is to migrate to a container orchestration platform like Kubernetes.

### 3.1. When to Migrate?

Migration should be considered when the daily task queue for schedule generation consistently backs up, indicating that the available Celery workers can no longer keep up with the number of tasks dispatched by the `master_schedule_generator`.

### 3.2. How Kubernetes Will Be Used

Kubernetes will provide **true elastic scaling** for our Celery workers.

- **Horizontal Pod Autoscaler (HPA):** We will deploy our Celery workers as a "Deployment" on a Kubernetes cluster (e.g., using Oracle OKE, Google GKE, or Amazon EKS).
- **Mechanism:** An HPA will be configured to monitor the length of the Celery task queue in Redis.
- **Automatic Scaling:**
    - When the `master_schedule_generator` dispatches thousands of tasks, the queue length will spike.
    - The HPA will detect this spike and automatically command the Kubernetes cluster to **add more Celery worker containers (pods)**. This is horizontal scaling. The cluster may even add new VMs ("nodes") to accommodate these new pods if necessary.
    - These new workers will immediately start processing tasks from the queue in parallel, clearing the backlog quickly.
    - Once the queue length drops below a certain threshold, the HPA will automatically terminate the extra worker pods to save resources and cost.

This approach ensures that we have exactly the right amount of processing power at any given moment, making the system massively scalable, resilient, and cost-effective, ready to handle millions of users without manual intervention.
