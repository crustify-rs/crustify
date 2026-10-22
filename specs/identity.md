Crustify's identity is the GitHub account `crustify-ai`. Its git identity is:

```text
crustify <crustify@berkeley.edu>
```

Every commit a Crustify agent makes is authored as this identity, whatever the
repository's git configuration says. The identity is passed to each commit explicitly:

```bash
git -c user.name=crustify -c user.email=crustify@berkeley.edu commit ...
```
