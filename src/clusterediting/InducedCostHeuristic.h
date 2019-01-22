#ifndef INDUCEDCOSTHEURISTICLIGHT_H
#define INDUCEDCOSTHEURISTICLIGHT_H

#include "EdgeHeap.h"
#include "ClusterEditingSolutionLight.h"

namespace ysk {

class InducedCostHeuristic {
  

public:
    InducedCostHeuristic(StaticSparseGraph& param_graph, bool param_pruneZeroEdges);
    ClusterEditingSolutionLight solve();

private:    
    void init();
    bool resolvePermanentForbidden();
    void setForbidden(const StaticSparseGraph::Edge e);
    void setPermanent(const StaticSparseGraph::Edge e);
    void setZero(const StaticSparseGraph::Edge e);
    void setToWeight(const StaticSparseGraph::Edge e, const StaticSparseGraph::EdgeWeight newWeight);
    
    /**
    * Updates icf and icp for the edge uw under the assumption that edge uv will be set to forbidden.
    */
    void updateTripleForbiddenUW(const StaticSparseGraph::EdgeWeight uv, const StaticSparseGraph::Edge uw, const StaticSparseGraph::EdgeWeight vw);

    /**
    * Updates icf and icp for the edge uw under the assumption that edge uv will be set to permanent.
    */
    void updateTriplePermanentUW(const StaticSparseGraph::EdgeWeight uv, const StaticSparseGraph::Edge uw, const StaticSparseGraph::EdgeWeight vw);
    
    /**
    * Updates icf and icp for the edge uw under the assumption that edge uv will be set to zero.
    */
    void updateTripleZeroUW(const StaticSparseGraph::EdgeWeight uv, const StaticSparseGraph::Edge uw, const StaticSparseGraph::EdgeWeight vw);
    
        /**
    * Updates icf and icp for the edge uw under the assumption that edge uv will be set to zero.
    */
    void updateTripleCustomWeightUW(const StaticSparseGraph::EdgeWeight uv, const StaticSparseGraph::EdgeWeight uv_new, const StaticSparseGraph::Edge uw, const StaticSparseGraph::EdgeWeight vw);
    
    bool pruneZeroEdges;
    StaticSparseGraph graph;
    EdgeHeap edgeHeap;
    StaticSparseGraph::EdgeWeight totalCost;
};

} // namespace ysk

#endif // INDUCEDCOSTHEURISTICLIGHT_H