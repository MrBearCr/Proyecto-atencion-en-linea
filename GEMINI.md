# GEMINI.md

## Project Overview

This project is a desktop application for customer management and logistics, developed in Python. Originally focused on client management and bulk WhatsApp messaging, it has evolved into a robust platform for **Logistic Management**, **Abastecimiento (Supply Chain)**, and **Global Stock Calculation**. The application features a premium GUI built with Tkinter and connects to a SQL Server database.

### Main Technologies

*   **Language:** Python
*   **GUI:** Tkinter
*   **Database:** SQL Server (via `pyodbc`)
*   **Testing:** `pytest`, `pytest-cov`
*   **Dependencies:** `cryptography`, `keyring`, `tkcalendar`, `requests`, `matplotlib`, `win10toast`, `Pillow`, `bcrypt`, `packaging`, `pyodbc`

### AI Skills Integration

The development and maintenance of this project are enhanced by a suite of **AI Skills**. These are specialized agentic capabilities that can be invoked for specific tasks:

*   **`systematic-debugging`**: Used for deep-diving into complex stack traces and hardware-specific issues.
*   **`ui-ux-pro-max`**: Ensures the Tkinter interface maintains a premium, modern aesthetic with consistent theme application.
*   **`test-driven-development`**: Guides the implementation of new features with comprehensive unit tests.
*   **`performance-optimization`**: Applied to optimize large dataset processing in modules like `exports.py`.

### Architecture

The application follows a modular architecture with the core logic separated into the `pal` directory:

*   `core`: Contains the main business logic, including authentication, session management, and permissions.
*   `infrastructure`: Manages the database connection and data access layer.
*   `services`: Implements critical business modules:
    *   `abastecimiento.py`: Supply chain and transfer management.
    *   `stock.py`: Real-time stock tracking and global stock calculation logic.
    *   `tra.py` / `mbrp.py`: Business-specific data processing.
    *   `exports.py`: High-performance data exporting services.
    *   `notifications.py`: WhatsApp and system notifications.
*   `ui`: Contains the user interface components (tabs, popups, and custom themes).

## Building and Running

### Prerequisites

*   Python 3
*   SQL Server
*   The required Python packages listed in `requirements.txt`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the database:**
    The application requires a `db_config.ini` file in the root directory to connect to the SQL Server database. The application will create a default `db_config.ini` if one is not found. The file should have the following structure:

    ```ini
    [Database]
    server = <your-server-address>
    database = <your-database-name>
    user = <your-username>
    password = <your-password>
    ```
    If `user` and `password` are left blank, the application will use Windows Authentication.

### Running the Application

To run the application, execute the `app.py` script:

```bash
python app.py
```

## Development Conventions

*   **Code Style:** The code generally follows PEP 8 style guidelines.
*   **Modularity:** The code is organized into modules with specific responsibilities, promoting separation of concerns.
*   **Error Handling:** The application includes error handling for database connections and other operations, with custom error codes defined in `pal/core/errors.py`.
*   **Security:** Credentials and sensitive information are handled using the `cryptography` and `keyring` libraries. Passwords are hashed using `bcrypt`.
*   **Logging:** The application uses the `logging` module for logging events and debugging information.
*   **Configuration:** Application settings, including database credentials and module configurations, are managed through the `db_config.ini` file.
*   **Database Schema:** The application automatically creates and migrates the necessary database tables upon initial connection. The schema includes tables for users, roles, permissions, sessions, and audit logs.
