// Shared original-document helpers; the goal-driven release library supplies navigation.
const sourceNames={'小林完整专栏':'小林 coding · 面试八股','小林图解完整专栏':'小林 coding · 图解专栏','Go面试宝典':'Go 面试宝典'};
function sourceLabel(source){return sourceNames[source]||source;}
function originalDocs(){return state.catalog.filter(a=>a.learning_unit??(a.path.startsWith('资料源/')&&!a.replaced_by_chapters));}
async function renderLibrary(){}
