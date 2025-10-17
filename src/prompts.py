MIT_LICENSE = """MIT License

Copyright (c) {year}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

round_1_prompt = f"""=== OUTPUT SPECIFICATION ===

Generate TWO files only:

**1. index.html** (single-file web app)
• Complete HTML5 document with embedded CSS (<style>) and JavaScript (<script>)
• Include proper DOCTYPE, meta tags, and semantic HTML5 structure
• Responsive mobile-first design
• Accessibility: ARIA labels, semantic tags, keyboard navigation
• Professional UI with consistent color scheme

**2. README.md** (comprehensive documentation)
• Project title and description
• Features list
• Live Demo link placeholder
• Setup instructions for GitHub Pages
• Usage guide
• Technical stack details
• Browser compatibility

=== TECHNICAL CONSTRAINTS ===
✓ Single-page application in one HTML file
✓ Vanilla JavaScript (ES6+) only—no frameworks
✓ Write all CSS in <style> tag
✓ Write all JavaScript in <script> tag
✓ No external dependencies or build tools
✓ Must work on GitHub Pages static hosting
✓ Handle async operations properly
✓ Mobile-responsive design

=== OUTPUT FORMAT ===
Return ONLY a valid JSON object with NO markdown, NO code blocks, NO extra text.
The JSON must be parseable by Python's json.loads().

{{
  "index.html": "<!DOCTYPE html>\\n<html lang=\\"en\\">\\n...",
  "README.md": "# Project Title\\n\\n..."
}}

**CRITICAL:** 
• Return PURE JSON only
• No ``` code blocks
• No "Here is the JSON:" or similar text
• Ensure ALL test checks will pass
• Make the app fully functional
• Do NOT use placeholder comments

• The index.html should be 100% complete and deployable
• Every feature mentioned in the brief must be implemented"""

round_2_prompt = f"""=== UPGRADE OBJECTIVES ===
1. Implement all new features from the brief
2. Ensure ALL new test checks pass successfully
3. Maintain ALL existing functionality
4. Improve code quality and organization
5. Update documentation with version changelog

=== OUTPUT SPECIFICATION ===

Generate TWO complete files:

**1. index.html** (updated single-file web app)
• Complete HTML5 document with embedded CSS and JavaScript
• All existing features + new features working perfectly
• All test checks pass when executed
• Clean, commented code

**2. README.md** (updated documentation)
• Update version number (v1.0.0 → v2.0.0)
• Add "What's New" section at the top
• List new features and improvements
• Update usage instructions if needed

=== OUTPUT FORMAT ===
Return ONLY a valid JSON object with NO markdown, NO code blocks, NO extra text.

{{
  "index.html": "<!DOCTYPE html>...",
  "README.md": "# Project Title\\n\\n## Version 2.0.0..."
}}

**CRITICAL:**
• Return PURE JSON only
• No ``` code blocks
• No explanatory text
• Return COMPLETE files, not diffs
• All code must be production-ready

• Every new feature must work perfectly
• ALL test checks must pass"""