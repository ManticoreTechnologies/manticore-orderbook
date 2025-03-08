module.exports = {
  title: 'Manticore OrderBook',
  tagline: 'A high-performance order book implementation for cryptocurrency exchanges',
  url: 'https://manticoretechnologies.github.io',
  baseUrl: '/manticore-orderbook/',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.png',
  organizationName: 'manticoretechnologies',
  projectName: 'manticore-orderbook',
  
  themeConfig: {
    navbar: {
      title: 'Manticore OrderBook',
      logo: {
        alt: 'Manticore Technologies Logo',
        src: 'img/logo.png',
      },
      items: [
        {
          to: 'docs/',
          activeBasePath: 'docs',
          label: 'Docs',
          position: 'left',
        },
        {
          href: 'https://github.com/manticoretechnologies/manticore-orderbook',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'Introduction',
              to: 'docs/',
            },
            {
              label: 'User Guide',
              to: 'docs/user-guide',
            },
            {
              label: 'API Reference',
              to: 'docs/api-reference',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'GitHub',
              href: 'https://github.com/manticoretechnologies/manticore-orderbook',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'Website',
              href: 'https://manticore.technology',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Manticore Technologies.`,
    },
  },
  
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          editUrl: 'https://github.com/manticoretechnologies/manticore-orderbook/edit/main/docusaurus-docs/',
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
}; 