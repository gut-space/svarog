def check_output(self, output: str, strings):
    """Checks if specified output (presumably stdout) has appropriate content. strings
    is a list of strings that are expected to be present. They're expected
    to appear in the specified order, but there may be other things
    printed in between them. Will assert if string is not found. """

    # Make sure we're dealing with a string, and not something similar (like bytes)
    output = str(output)

    offset = 0
    for s in strings:
        new_offset = output.find(s, offset)

        self.assertNotEqual(new_offset, -1, "Not found an expected string: '%s'" % s)
        # string found, move to its end and continue searching
        offset = new_offset + len(s)
