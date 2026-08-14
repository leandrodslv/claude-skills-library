/**
 * Configuration commitlint — Conventional Commits.
 * Installation :
 *   npm i -D @commitlint/cli @commitlint/config-conventional husky
 *   npx husky init
 *   cp ~/.claude/skills/git-github/assets/commitlint.config.js .
 *   echo 'npx --no -- commitlint --edit "$1"' > .husky/commit-msg
 */
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'perf',
        'revert',
        'docs',
        'style',
        'refactor',
        'test',
        'build',
        'ci',
        'chore',
      ],
    ],
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'type-case': [2, 'always', 'lower-case'],
    'scope-case': [2, 'always', 'lower-case'],
    'header-max-length': [2, 'always', 72],
    'body-leading-blank': [2, 'always'],
    'footer-leading-blank': [2, 'always'],
  },
};
