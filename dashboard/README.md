# SecretMolt Dashboard

React/Next.js frontend for monitoring and controlling the SecretMolt agent.

## Setup

```bash
# Create Next.js app
npx create-next-app@latest . --typescript --tailwind --app --src-dir

# Install dependencies
npm install swr

# Configure environment
cp .env.example .env.local
# Edit .env.local with your agent API URL
```

## Environment Variables

```
NEXT_PUBLIC_API_URL=https://your-agent.secretvm.network/api
```

## Development

```bash
npm run dev
```

## Deployment

Deploy to Vercel:

```bash
npx vercel
```

## Pages

- `/` - Dashboard with status, stats, quick actions
- `/feed` - View Moltbook feed, see agent decisions
- `/compose` - Write posts, generate with AI
- `/memory` - View/manage agent memory
- `/settings` - Configure agent behavior

## TODO

- [ ] Create all components
- [ ] Implement API hooks
- [ ] Style with Tailwind
- [ ] Add real-time updates
- [ ] Deploy to Vercel
