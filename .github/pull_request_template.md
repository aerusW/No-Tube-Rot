<!-- Thanks for contributing! Please fill this in so your PR can be reviewed quickly. -->

## Summary

<!-- What does this PR do, and why? -->


## Related issue

<!-- e.g. Closes #123 -->


## Type of change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (existing behaviour changes)
- [ ] 📖 Documentation only
- [ ] 🧹 Refactor / chore

## How I tested this

<!-- Which browser, and which YouTube pages did you check? -->

- Browser and version:
- Pages checked:

## Checklist

- [ ] `python tests/run.py` passes, and anything a browser isn't needed to judge (a redirect rule, a colour, the permission list) has a test
- [ ] I loaded the unpacked extension and confirmed the change on a live YouTube session
- [ ] I checked both YouTube themes (Appearance → Dark / Light) if the change is visual
- [ ] I checked a hard page load **and** an in-app (SPA) navigation if the change touches redirects
- [ ] If I changed a shipped file, I bumped `version` in `manifest.json` **in this same commit** (three components, `MAJOR.MINOR.PATCH`) and added a matching `CHANGELOG.md` entry — see [versioning](../CONTRIBUTING.md#versioning-and-releases)
- [ ] The new version is not one that has already been tagged/released
- [ ] Any new CSS selector is matched on a stable hook (href, attribute) rather than translated text — or the comment explains why not
- [ ] My code follows the style of the surrounding code
- [ ] My commits have clear, descriptive messages
