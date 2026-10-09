# Website

This website is built using [Docusaurus](https://docusaurus.io/), a modern static website generator.

## Local Installation

```bash
npm install
```

**Note**: feel free to use the package manager of your choice.

```bash
npm run start
```

This command starts a local development server and opens up a browser window. Most changes are reflected live without having to restart the server.

## Build

```bash
npm run build
```

This command generates static content into the `build` directory and can be served using any static contents hosting service.

## Or View the documentation with Docker

Install and start Docker Desktop, then run this command from the `agrosense-docs` directory:

```bash
docker compose up --build -d
```

Open [http://localhost:8080](http://localhost:8080) to view the documentation. Docker builds the site and serves it with Nginx, so Node.js and the project packages do not need to be installed on the host machine.

To use a different local port, create a `.env` file in this directory with `DOCS_PORT=8081`. Stop the service with:

```bash
docker compose down
```

## Deployment

Using SSH:

```bash
USE_SSH=true npm run deploy
```

Not using SSH:

```bash
GIT_USER=<Your GitHub username> npm run deploy
```

If you are using GitHub Pages for hosting, this command is a convenient way to build the website and push to the `gh-pages` branch.
