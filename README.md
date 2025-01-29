# smtpy
A mail client that uses an email script.

This was made for replicating email issues in a support engineering role. A useful tool
for creating reproduction scenarios that depend on specific email data and/or connection
properties.

Email data and connection parameters are stored in an _smtpyfile_ which can then be
executed by _smtpy_ to submit it to a mail server.

Usage:

```
$ ./smtpy.py smtpyfile
```

See the included _smtpyfile_ for additional documentation on what settings you can use.
