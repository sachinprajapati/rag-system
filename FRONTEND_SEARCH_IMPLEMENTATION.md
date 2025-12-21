# Frontend Implementation - Search Method Selection

## Overview
Added search method selection UI to the frontend, allowing users to choose between Vector, Keyword, and Hybrid search strategies.

## Changes Made

### 1. Updated API Service
**File**: [src/services/api.ts](frontend/src/services/api.ts)

**Change**: Added `search_method` parameter to `queryRAGSystem` function
```typescript
export const queryRAGSystem = async (
    query: string, 
    top_k: number = 5,
    search_method: 'vector' | 'keyword' | 'hybrid' = 'hybrid'
) => {
    const response = await apiClient.post('/query', { query, top_k, search_method });
    return response.data;
};
```

---

### 2. Enhanced QueryInterface Component
**File**: [src/components/QueryInterface.tsx](frontend/src/components/QueryInterface.tsx)

**New Features**:
- ✅ Search method dropdown selector (Hybrid, Vector, Keyword)
- ✅ Top-K results slider (1-20)
- ✅ Contextual help text for each method
- ✅ Display search method used in results
- ✅ Integrated info panel

**UI Components Added**:

#### Search Method Selector
```tsx
<select value={searchMethod} onChange={(e) => setSearchMethod(e.target.value)}>
    <option value="hybrid">🔀 Hybrid (Recommended)</option>
    <option value="vector">🧠 Vector (Semantic)</option>
    <option value="keyword">🔍 Keyword (BM25)</option>
</select>
```

#### Top-K Input
```tsx
<input
    type="number"
    value={topK}
    onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
    min="1"
    max="20"
/>
```

---

### 3. New Info Component
**File**: [src/components/SearchMethodInfo.tsx](frontend/src/components/SearchMethodInfo.tsx)

**Purpose**: Collapsible panel explaining each search method

**Content**:
- 🔀 **Hybrid**: Combines semantic + keyword (recommended)
- 🧠 **Vector**: AI embeddings for meaning and context
- 🔍 **Keyword**: BM25 for exact terms and technical jargon
- 💡 **Pro Tips**: When to use each method

**Features**:
- Expandable/collapsible (click header)
- Examples for each method
- Visual styling with icons
- Pro tip section

---

### 4. Updated Type Definitions
**File**: [src/types/index.ts](frontend/src/types/index.ts)

**New Types**:
```typescript
export type SearchMethod = 'vector' | 'keyword' | 'hybrid';

export interface RetrievedDocument {
    text: string;
    file_name: string;
    score: number;
    rank?: number;
    search_method?: string;
    chunk_index?: number;
    tenant_id?: string;
}

export interface RAGQueryResponse {
    query: string;
    answer: string;
    retrieved_documents: RetrievedDocument[];
    sources: string[];
    tenant_id?: string;
}
```

---

## User Interface

### Query Form Layout
```
┌─────────────────────────────────────────────────────┐
│ Query the RAG System                                │
├─────────────────────────────────────────────────────┤
│ ℹ️ Search Methods Explained              [▶]       │
├─────────────────────────────────────────────────────┤
│ [Query Input Field................................] │
│                                                      │
│ Search Method:           │  Results (Top-K):        │
│ [🔀 Hybrid (Recommended)▼]  │  [5      ]            │
│ ✨ Combines semantic + exact matching              │
│                                                      │
│              [Submit Query]                          │
└─────────────────────────────────────────────────────┘
```

### Results Display
```
┌─────────────────────────────────────────────────────┐
│ Answer:                        [hybrid search]      │
├─────────────────────────────────────────────────────┤
│ Based on the retrieved documents...                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Retrieved Documents (5):                            │
├─────────────────────────────────────────────────────┤
│ document.pdf                    Score: 0.856        │
│ Document chunk text content...                      │
└─────────────────────────────────────────────────────┘
```

---

## Usage Examples

### Example 1: Hybrid Search (Default)
**User Action**: Select "🔀 Hybrid (Recommended)"
**Query**: "What are the employee benefits?"

**What Happens**:
- Frontend sends: `{ query: "...", search_method: "hybrid", top_k: 5 }`
- Backend uses: Vector search + BM25 keyword search + Fusion
- Results: Best of both semantic understanding and exact keyword matching

---

### Example 2: Vector Search
**User Action**: Select "🧠 Vector (Semantic)"
**Query**: "Tell me about workplace perks"

**What Happens**:
- Frontend sends: `{ query: "...", search_method: "vector", top_k: 5 }`
- Backend uses: Only FAISS vector search with embeddings
- Results: Finds semantically similar content like "employee benefits", "compensation", "rewards"

---

### Example 3: Keyword Search
**User Action**: Select "🔍 Keyword (BM25)"
**Query**: "ISO 27001 certification"

**What Happens**:
- Frontend sends: `{ query: "...", search_method: "keyword", top_k: 5 }`
- Backend uses: Only BM25 keyword matching
- Results: Documents with exact mentions of "ISO 27001"

---

## Help Text by Method

| Method | Help Text |
|--------|-----------|
| **Hybrid** | ✨ Combines semantic understanding + exact keyword matching |
| **Vector** | 🎯 Best for conceptual queries and paraphrasing |
| **Keyword** | 📝 Best for specific terms and exact matches |

---

## Info Panel Content

When expanded, shows:

### 🔀 Hybrid (Recommended) ⭐
- **Description**: Best for most queries - combines semantic + keyword
- **Example**: "What are the health insurance options?" → Finds "medical coverage" semantically while prioritizing "health insurance" exactly
- **When to use**: Default choice for balanced results

### 🧠 Vector (Semantic Search)
- **Description**: Uses AI embeddings to understand meaning and context
- **Example**: "Tell me about employee benefits" → Also finds "compensation package", "perks", "workplace rewards"
- **When to use**: Conceptual queries, paraphrasing, finding related content

### 🔍 Keyword (BM25)
- **Description**: Traditional keyword matching using BM25 algorithm
- **Example**: "ISO 27001 certification" → Prioritizes exact matches for "ISO 27001"
- **When to use**: Specific terms, technical jargon, IDs, exact phrase matches

### 💡 Pro Tip
Start with **Hybrid** for balanced results. Switch to **Vector** for conceptual questions or **Keyword** for precise technical terms.

---

## State Management

**New State Variables**:
```typescript
const [searchMethod, setSearchMethod] = useState<SearchMethod>('hybrid');
const [topK, setTopK] = useState(5);
```

**State Flow**:
1. User selects search method → Updates `searchMethod` state
2. User adjusts top-k slider → Updates `topK` state
3. User submits query → Calls `queryRAGSystem(query, topK, searchMethod)`
4. Backend processes with selected method
5. Results displayed with method indicator

---

## Responsive Design

**Layout**:
- Search method selector: Full width on mobile, half width on desktop
- Top-K input: Fixed width (120px)
- Help text: Below selector, updates dynamically
- Info panel: Collapsible to save space

**Styling**:
- Clean, modern UI with consistent spacing
- Color-coded help text (#666)
- Highlighted info panel (#f0f7ff background)
- Method badge in results (#e0e0e0 background)

---

## Integration with Backend

**API Request Format**:
```json
{
  "query": "What is the salary structure?",
  "top_k": 5,
  "search_method": "hybrid"
}
```

**API Response Format**:
```json
{
  "query": "What is the salary structure?",
  "answer": "Based on the documents...",
  "retrieved_documents": [
    {
      "text": "...",
      "file_name": "salary.pdf",
      "score": 0.856,
      "rank": 1,
      "search_method": "hybrid"
    }
  ],
  "sources": ["salary.pdf"]
}
```

---

## Files Modified

1. ✅ **frontend/src/services/api.ts** - Added search_method parameter
2. ✅ **frontend/src/components/QueryInterface.tsx** - Search method selector UI
3. ✅ **frontend/src/components/SearchMethodInfo.tsx** - New info component
4. ✅ **frontend/src/types/index.ts** - New type definitions

---

## Testing

### Manual Test Cases

**Test 1: Default Hybrid Search**
1. Open application
2. Verify "Hybrid" is selected by default
3. Enter query: "What are the benefits?"
4. Submit and verify results show "hybrid search" badge

**Test 2: Switch to Vector Search**
1. Select "Vector (Semantic)" from dropdown
2. Verify help text changes to "Best for conceptual queries..."
3. Enter query: "Tell me about perks"
4. Submit and verify semantic results

**Test 3: Switch to Keyword Search**
1. Select "Keyword (BM25)" from dropdown
2. Verify help text changes to "Best for specific terms..."
3. Enter query: "ISO 27001"
4. Submit and verify exact matches

**Test 4: Adjust Top-K**
1. Change top-k from 5 to 10
2. Submit query
3. Verify 10 results returned (if available)

**Test 5: Info Panel**
1. Click "Search Methods Explained" header
2. Verify panel expands with detailed info
3. Click again to collapse

---

## Browser Compatibility

- ✅ Chrome/Edge (Chromium)
- ✅ Firefox
- ✅ Safari
- ✅ Mobile browsers

---

## Accessibility

- ✅ Keyboard navigation (Tab/Shift+Tab)
- ✅ Screen reader friendly labels
- ✅ Semantic HTML (select, input)
- ✅ Clear visual indicators
- ✅ Collapsible content for focus management

---

## Future Enhancements

### Advanced Options Panel
- [ ] Fusion method selector (Weighted vs RRF)
- [ ] Weight sliders for hybrid (vector vs keyword)
- [ ] Response format options
- [ ] Language selection

### Visual Improvements
- [ ] Search method icons/illustrations
- [ ] Performance metrics display (query time)
- [ ] Result preview/snippet highlighting
- [ ] Comparison mode (side-by-side methods)

### UX Enhancements
- [ ] Save preferred search method to localStorage
- [ ] Query history with method used
- [ ] Smart method suggestions based on query
- [ ] A/B testing different methods

---

## Summary

✅ **Search method selection** added to frontend
✅ **Three methods available**: Vector, Keyword, Hybrid
✅ **Info panel** explains each method with examples
✅ **Top-K adjustment** for result count
✅ **Visual indicators** show method used in results
✅ **Responsive design** works on all screen sizes

Users can now choose the optimal search strategy for their queries, with helpful guidance on when to use each method.
