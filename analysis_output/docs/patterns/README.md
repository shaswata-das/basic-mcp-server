# Design Patterns

The codebase follows common Python best practices:

- **Modular structure** separating configuration, core server logic, handlers, and services.
- **Dependency injection** style initialization where services are passed to handlers during setup.
- **Asynchronous programming** using `asyncio` to handle multiple transports concurrently.
