# System Architecture Diagram (For IEEE Paper)

You can copy and paste the Mermaid code below directly into any markdown viewer that supports Mermaid (like GitHub), or use [Mermaid Live Editor](https://mermaid.live/) to export it as a high-resolution PNG for your Capstone manuscript.

```mermaid
graph TD
    %% Define Styles
    classDef input fill:#1E293B,stroke:#94A3B8,stroke-width:2px,color:#F8FAFC;
    classDef moduleA fill:#78350F,stroke:#F59E0B,stroke-width:2px,color:#F8FAFC;
    classDef moduleB fill:#064E3B,stroke:#10B981,stroke-width:2px,color:#F8FAFC;
    classDef moduleC fill:#4C1D95,stroke:#8B5CF6,stroke-width:2px,color:#F8FAFC;
    classDef meta fill:#1E3A8A,stroke:#3B82F6,stroke-width:2px,color:#F8FAFC;
    classDef output_clean fill:#064E3B,stroke:#10B981,stroke-width:3px,color:#F8FAFC;
    classDef output_adv fill:#7F1D1D,stroke:#EF4444,stroke-width:3px,color:#F8FAFC;

    %% Nodes
    Input[("Raw Candidate Resume (PDF/Text)")]:::input
    
    subgraph Feature Extraction Layer
        ModA["Module A\n(Statistical Density)"]:::moduleA
        ModB["Module B\n(PDF Structural Forensics)"]:::moduleB
        ModC["Module C\n(Semantic Coherence / MiniLM)"]:::moduleC
    end
    
    subgraph Ensemble Layer
        Meta["Meta-Classifier\n(Logistic Regression)"]:::meta
        Shap["SHAP Explainer\n(Attribution & Fairness)"]:::meta
    end
    
    OutClean["Legitimate Resume\n(Passed to ATS)"]:::output_clean
    OutAdv["Adversarial Injection\n(Flagged & Quarantined)"]:::output_adv

    %% Connections
    Input --> ModA
    Input --> ModB
    Input --> ModC
    
    ModA -- "Density Score" --> Meta
    ModB -- "Structural Score" --> Meta
    ModC -- "Variance Score" --> Meta
    
    Meta <--> Shap
    
    Meta -- "P(Adversarial) < 0.5" --> OutClean
    Meta -- "P(Adversarial) >= 0.5" --> OutAdv
```
