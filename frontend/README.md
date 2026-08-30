CryptoTrace Frontend

This is a simple React + Vite frontend for the CryptoTrace demo.

Quick start (after installing Node.js):

cd d:\OneDrive\Documents\CRYPTO-TRACE\frontend
npm install
npm run dev

Notes
- The frontend proxies /trace and /reports to http://127.0.0.1:8000 (see vite.config.ts). Start backend first.
- CaseForm posts to '/trace' and App shows a Download PDF link to '/reports/{case_id}.pdf'
- Cytoscape is used for graph visualization; the GraphView currently uses a simple layout and should be refined for production.
