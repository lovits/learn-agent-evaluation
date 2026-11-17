# Upload API

POST /upload requires the API token in the X-Project-Token header.
The maximum file size is 1048576 bytes (1 MiB).
A larger upload returns HTTP 413. Check the file size before sending.
