import axe from 'axe-core';

export interface A11yCheckOptions {
  rules?: Record<string, { enabled: boolean }>;
  runOnly?: string[];
}

export interface A11yViolation {
  id: string;
  impact?: 'minor' | 'moderate' | 'serious' | 'critical' | null;
  description: string;
  help: string;
  helpUrl: string;
  nodes: Array<{
    html: string;
    target: string[];
    failureSummary?: string;
  }>;
}

/**
 * Runs an axe-core accessibility audit on the given DOM container.
 * Tests against WCAG 2.0, 2.1, and 2.2 Level A and AA standards.
 */
export async function auditA11y(
  container: Element | Document | string = document.body,
  options: A11yCheckOptions = {}
): Promise<{ violations: A11yViolation[]; passesCount: number }> {
  const runOnly = options.runOnly || [
    'wcag2a',
    'wcag2aa',
    'wcag21a',
    'wcag21aa',
    'wcag22aa',
    'best-practice',
  ];

  const results = await axe.run(container, {
    runOnly: {
      type: 'tag',
      values: runOnly,
    },
    rules: {
      // In JSDOM, color-contrast cannot be reliably computed because layout/computed CSS colors are mocked
      'color-contrast': { enabled: false },
      ...options.rules,
    },
  });

  const violations: A11yViolation[] = results.violations.map((v) => ({
    id: v.id,
    impact: v.impact,
    description: v.description,
    help: v.help,
    helpUrl: v.helpUrl,
    nodes: v.nodes.map((n) => ({
      html: n.html,
      target: n.target as string[],
      failureSummary: n.failureSummary,
    })),
  }));

  return {
    violations,
    passesCount: results.passes.length,
  };
}

/**
 * Custom assertion helper to ensure an element has zero accessibility violations.
 */
export async function expectNoA11yViolations(
  container: Element | Document | string = document.body,
  options: A11yCheckOptions = {}
): Promise<void> {
  const { violations } = await auditA11y(container, options);

  if (violations.length > 0) {
    const report = violations
      .map(
        (v) =>
          `[${v.impact?.toUpperCase() || 'UNKNOWN'}] ${v.id}: ${v.help}\n  Nodes:\n${v.nodes
            .map((n) => `    - ${n.html} (Target: ${n.target.join(' ')})`)
            .join('\n')}`
      )
      .join('\n\n');
    throw new Error(`Accessibility violations detected (${violations.length}):\n${report}`);
  }
}
