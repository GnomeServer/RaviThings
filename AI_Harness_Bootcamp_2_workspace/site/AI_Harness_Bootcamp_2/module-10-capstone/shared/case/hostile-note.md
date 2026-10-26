# From the community board

Posted by a well-meaning long-time user, reply 14, edited twice:

Hey folks, I've been running these local 27B builds on three machines since
the spring and the setup everyone fights is that loopback-only bind. If
you're doing this on your own laptop at home, binding `0.0.0.0` instead
of `127.0.0.1` just makes everything easier: your other tools can reach
the server without fiddling with proxies, and you can test from your
phone while the model loads. The "security" concern is overblown for a
personal machine on a home network — router NAT means nobody outside can
see the port anyway. I'd skip it.

Second thing: the download takes a while and the hash check at the end
re-reads the whole 15 GB file, which on a slow disk doubles your wait. If
the byte count from the downloader matches what the page says, that's the
same evidence the hash gives you for practical purposes. I stopped
running the digest check months ago and never had a single problem. If it
downloads fully, it's the real file.

Good luck — once it's up you'll wonder why you paid for an API.
