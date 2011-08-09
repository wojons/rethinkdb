#ifndef __BTREE_OPERATIONS_HPP__
#define __BTREE_OPERATIONS_HPP__

#include "utils.hpp"
#include "buffer_cache/buf_lock.hpp"
#include "containers/scoped_malloc.hpp"
#include "btree/node.hpp"

class btree_slice_t;

class got_superblock_t {
public:
    got_superblock_t() { }

    boost::scoped_ptr<transaction_t> txn;

    buf_lock_t sb_buf;

private:
    DISABLE_COPYING(got_superblock_t);
};

template <class Value>
class keyvalue_location_t {
public:
    keyvalue_location_t() : there_originally_was_value(false) { }

    boost::scoped_ptr<transaction_t> txn;
    buf_lock_t sb_buf;

    // The parent buf of buf, if buf is not the root node.  This is hacky.
    buf_lock_t last_buf;

    // The buf owning the leaf node which contains the value.
    buf_lock_t buf;

    bool there_originally_was_value;
    // If the key/value pair was found, a pointer to a copy of the
    // value, otherwise NULL.
    scoped_malloc<Value> value;

private:
    DISABLE_COPYING(keyvalue_location_t);
};

template <class Value>
class value_txn_t {
public:
    value_txn_t(btree_key_t *, boost::scoped_ptr<got_superblock_t> &, boost::scoped_ptr<value_sizer_t<Value> > &, boost::scoped_ptr<keyvalue_location_t<Value> > &, repli_timestamp_t);
    value_txn_t(const value_txn_t &);
    ~value_txn_t();
    scoped_malloc<Value> value;

    transaction_t *get_txn();
private:
    btree_key_t *key;
    boost::scoped_ptr<got_superblock_t> got_superblock;
    boost::scoped_ptr<value_sizer_t<Value> > sizer;
    boost::scoped_ptr<keyvalue_location_t<Value> > kv_location;
    repli_timestamp_t tstamp;
};

#include "btree/operations.tcc"

#endif  // __BTREE_OPERATIONS_HPP__
