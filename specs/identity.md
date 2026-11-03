Crustify's identity is the GitHub account `crustify-ai`. Its git identity is:

```text
crustify <crustify@berkeley.edu>
```

A campaign's commits carry the identity its settings name, the `identity` answer of
`crustify/CRUSTIFY.md`: an author, and any co-authors, each as `Name <email>`. The default,
when the question is left unanswered, is Crustify's identity as the author, with no
co-author.

Every commit of the campaign is authored and committed as that author, whatever the
repository's git configuration says, and its message ends with one `Co-Authored-By:`
trailer per co-author and no other. The identity is passed to each commit explicitly. For
example, under the default:

```bash
git -c user.name=crustify -c user.email=crustify@berkeley.edu commit ...
```

and with `author: Marius Momeu <marius.momeu@berkeley.edu>, co-authors: crustify
<crustify@berkeley.edu>`:

```bash
git -c "user.name=Marius Momeu" -c user.email=marius.momeu@berkeley.edu commit -F - <<'MSG'
<subject>

<body>

Co-Authored-By: crustify <crustify@berkeley.edu>
MSG
```
