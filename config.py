EMBEDDING_MODEL = "all-MiniLM-L6-v2"

TOPICS = {
    "Time Complexity": [
        "time complexity",
        "complexity",
        "growth rate",
        "worst-case",
        "worst case",
        "best case",
        "average case",
        "analyzing an algorithm",
        "analyzing algorithm",
    ],
    "Asymptotic Notation": [
        "big o",
        "big omega",
        "big-oh",
        "asymptotic",
        "o notation",
        "o(",
        "o(g(n))",
        "n0",
        "c*n",
        "omega(",
        "theta(",
        "θ(",
        "prove the following given function",
        "f(n) = o",
        "f(n)=o",
    ],
    "Recurrence Relations": [
        "recurrence",
        "master theorem",
        "master method",
        "back substitution",
        "backward substitution",
        "recursive factorial",
        "t(n)",
    ],
    "Arrays": ["array", "one dimensional array"],
    "Stack": ["stack", "push", "pop", "infix", "postfix", "reverse polish"],
    "Queue": ["queue", "enqueue", "dequeue", "circular queue"],
    "Linked List": [
        "linked list",
        "singly linked list",
        "doubly linked list",
        "circular single linked list",
        "create two lists",
        "two lists",
        "display both the lists",
        "insertend",
        "insertinbetween",
        "deletenode",
    ],
    "Polynomial Manipulation": ["polynomial"],
    "Algorithm Basics": [
        "algorithm development",
        "properties of an algorithm",
        "define algorithm",
        "stages of algorithm",
    ],
    "Algorithm Correctness": [
        "proof of correctness",
        "prove the correctness",
        "loop invariant",
        "correctness of algorithm",
    ],
    "Linear Search": ["linear search"],
    "Binary Search": ["binary search"],
    "Bubble Sort": ["bubble sort", "bubblesort"],
    "Insertion Sort": ["insertion sort"],
    "Merge Sort": ["merge sort"],
    "Quick Sort": ["quicksort", "quick sort"],
    "Counting Sort": ["counting sort"],
    "Complexity Analysis (sorting-specific)": [
        "sorting complexity",
        "sort algorithm complexity",
        "sort"
    ],
    "Binary Trees": [
        "binary tree",
        "generic tree",
        "general tree",
        "expression tree",
        "terminal nodes",
        "terminal node",
        "non-terminal",
        "internal nodes",
        "internal node",
        "strictly binary tree",
        "complete binary tree",
    ],
    "BST": ["bst", "binary search tree"],
    "Tree Traversals": ["traversal", "inorder", "preorder", "postorder", "level order"],
    "2-3 Trees": ["2-3 tree", "2 3 tree"],
    "Heap": ["heap"],
    "Priority Queue": ["priority queue"],
    "AVL Rotations": ["avl", "rotation"],
    "BFS": ["bfs", "breadth first"],
    "DFS": ["dfs", "depth first"],
    "Dijkstra": ["dijkstra", "single source shortest path", "shortest path"],
    "Minimum Spanning Tree": ["minimum spanning tree", "mst"],
    "Prim": ["prim", "prim's algorithm"],
    "Kruskal": ["kruskal"],
    "Hash Functions": ["hash function"],
    "Collision Resolution": ["collision", "collision resolution"],
    "Separate Chaining": ["separate chaining", "chaining"],
    "Open Addressing": ["open addressing"],
}

TOPIC_PROTOTYPES = {
    "Time Complexity": [
        "find the time complexity of an algorithm",
        "analyze worst case, best case or average case complexity",
        "compute running time or growth rate of the given code",
    ],
    "Asymptotic Notation": [
        "prove f of n belongs to big O of g of n",
        "find c and n0 for asymptotic notation",
        "determine big O, big omega, or theta notation",
    ],
    "Recurrence Relations": [
        "solve the recurrence relation using master theorem",
        "analyze T of n using recurrence tree or back substitution",
        "find the complexity of a recursive relation",
    ],
    "Arrays": [
        "perform operations on a one dimensional array",
        "design or analyze an array based solution",
        "search or arrange elements in an array",
    ],
    "Stack": [
        "convert infix to postfix using stack",
        "perform push and pop operations on a stack",
        "evaluate or manipulate expressions using stack",
    ],
    "Queue": [
        "explain circular queue and its operations",
        "perform enqueue and dequeue operations",
        "illustrate linear queue or circular queue behavior",
    ],
    "Linked List": [
        "create or manipulate a linked list",
        "insert delete or traverse nodes in a linked list",
        "design a circular single linked list",
    ],
    "Polynomial Manipulation": [
        "represent and manipulate a polynomial",
        "perform polynomial addition using linked representation",
    ],
    "Algorithm Basics": [
        "define an algorithm and list properties of an algorithm",
        "describe stages of algorithm development",
        "explain the general plan for algorithm analysis",
    ],
    "Algorithm Correctness": [
        "prove correctness of an algorithm using loop invariant",
        "write proof of correctness for a specified algorithm",
        "establish initialization maintenance and termination",
    ],
    "Linear Search": [
        "devise linear search algorithm",
        "search an element using linear search",
        "prove correctness of linear search",
    ],
    "Binary Search": [
        "search an element using binary search",
        "analyze binary search algorithm",
    ],
    "Insertion Sort": [
        "perform insertion sort and trace the passes",
        "analyze insertion sort algorithm",
    ],
    "Bubble Sort": [
        "perform bubble sort and trace the passes",
        "analyze bubble sort algorithm and swapping",
        "improve best case complexity of bubble sort",
    ],
    "Merge Sort": [
        "sort using merge sort",
        "analyze merge sort and merging process",
    ],
    "Quick Sort": [
        "sort using quick sort",
        "analyze partition and quicksort recursion",
    ],
    "Counting Sort": [
        "sort using counting sort",
        "analyze counting sort algorithm",
    ],
    "Complexity Analysis (sorting-specific)": [
        "compare best case and worst case complexity of sorting algorithms",
        "analyze complexity of a sorting algorithm",
    ],
    "Binary Trees": [
        "construct or represent a binary tree",
        "convert general tree into binary tree",
        "draw strict complete or expression trees",
        "count terminal and internal nodes in a tree",
    ],
    "BST": [
        "construct or search in a binary search tree",
        "insert delete and trace nodes in a BST",
    ],
    "Tree Traversals": [
        "perform inorder preorder postorder traversal",
        "trace tree traversal order",
    ],
    "2-3 Trees": [
        "insert or search in a 2-3 tree",
        "analyze balancing in a 2-3 tree",
    ],
    "Heap": [
        "build a min heap or max heap",
        "insert delete and trace heap operations",
    ],
    "Priority Queue": [
        "implement or analyze a priority queue",
        "use heap as a priority queue",
    ],
    "AVL Rotations": [
        "perform AVL insertion and balancing rotations",
        "trace AVL left rotation right rotation or double rotation",
    ],
    "BFS": [
        "perform breadth first search on a graph",
        "trace bfs vertex visitation order",
    ],
    "DFS": [
        "perform depth first search on a graph",
        "trace dfs vertex visitation order",
    ],
    "Dijkstra": [
        "find shortest path using dijkstra algorithm",
        "trace dijkstra table for weighted graph",
    ],
    "Minimum Spanning Tree": [
        "find minimum spanning tree using graph algorithms",
        "compare prim and kruskal algorithms for minimum spanning tree",
    ],
    "Prim": [
        "find minimum spanning tree using prim algorithm",
        "trace prim algorithm on a graph",
    ],
    "Kruskal": [
        "find minimum spanning tree using kruskal algorithm",
        "trace kruskal algorithm and chosen edges",
    ],
    "Hash Functions": [
        "apply a hash function to keys",
        "compute hash values and map keys into a table",
    ],
    "Collision Resolution": [
        "resolve collisions in hashing",
        "analyze collision handling in a hash table",
    ],
    "Separate Chaining": [
        "resolve collisions using separate chaining",
        "build chained hash table representation",
    ],
    "Open Addressing": [
        "resolve collisions using open addressing",
        "use probing to insert keys into hash table",
    ],
}

BLOOM_RULES = {
    "Remember": ["define", "what is", "list"],
    "Understand": ["explain", "describe", "write a note"],
    "Apply": ["solve", "convert", "implement", "perform"],
    "Analyze": ["analyze", "compare", "prove", "arrange", "plot"],
    "Create": ["design"],
}

QA_MARKERS = [
    "answer",
    "ans.",
    "ans:",
    "solution",
    "sol.",
    "sol:",
]
