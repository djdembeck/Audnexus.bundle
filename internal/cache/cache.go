package cache

import (
	"sync"
	"time"
)

type Cache struct {
	mu    sync.RWMutex
	items map[string]cacheItem
}

type cacheItem struct {
	value      interface{}
	expiration int64
}

func New() *Cache {
	c := &Cache{
		items: make(map[string]cacheItem),
	}
	go c.cleanup()
	return c
}

func (c *Cache) Set(key string, value interface{}, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.items[key] = cacheItem{
		value:      value,
		expiration: time.Now().Add(ttl).UnixNano(),
	}
}

func (c *Cache) Get(key string) (interface{}, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	item, found := c.items[key]
	if !found {
		return nil, false
	}
	if time.Now().UnixNano() > item.expiration {
		return nil, false
	}
	return item.value, true
}

func (c *Cache) cleanup() {
	for {
		time.Sleep(5 * time.Minute)
		c.mu.Lock()
		now := time.Now().UnixNano()
		for key, item := range c.items {
			if now > item.expiration {
				delete(c.items, key)
			}
		}
		c.mu.Unlock()
	}
}
