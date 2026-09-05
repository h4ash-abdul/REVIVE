import re
with open('frontend/src/pages/CaseDetail.tsx', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('  // eslint-disable-next-line react-hooks/exhaustive-deps\n  useEffect', '  useEffect')
c = c.replace('  }, [id])', '    // eslint-disable-next-line react-hooks/exhaustive-deps\n  }, [id])')

with open('frontend/src/pages/CaseDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(c)
